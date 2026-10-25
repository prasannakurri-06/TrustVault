
import os
import secrets
from pathlib import Path
from datetime import datetime, timezone

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, abort, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_


# ---------------- CONFIGURATION ----------------

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEY_FILE = BASE_DIR / ".trustvault_secret_key"


def get_secret_key():
    env_key = os.environ.get("TRUSTVAULT_SECRET_KEY")
    if env_key:
        return env_key

    if SECRET_KEY_FILE.exists():
        key = SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key

    key = secrets.token_hex(32)
    with open(SECRET_KEY_FILE, "x", encoding="utf-8") as f:
        f.write(key)
    return key


app = Flask(__name__)

app.config["SECRET_KEY"] = get_secret_key()
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + str(BASE_DIR / "trustvault.db").replace("\\", "/")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

# Login session settings
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_REFRESH_EACH_REQUEST"] = False
app.config["REMEMBER_COOKIE_DURATION"] = 0
app.config["REMEMBER_COOKIE_REFRESH_EACH_REQUEST"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

ALLOWED_EXTENSIONS = {"pdf", "txt", "png", "jpg", "jpeg", "docx"}


def utc_now():
    return datetime.now(timezone.utc)


# ---------------- DATABASE MODELS ----------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="Viewer")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), unique=True, nullable=False)
    owner_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    uploaded_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    shares = db.relationship(
        "DocumentShare",
        backref="document",
        lazy=True,
        cascade="all, delete-orphan",
    )


class DocumentShare(db.Model):
    __tablename__ = "document_shares"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(
        db.Integer, db.ForeignKey("document.id"), nullable=False
    )
    owner_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    shared_with_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    permission = db.Column(db.String(10), nullable=False, default="read")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    recipient = db.relationship("User", foreign_keys=[shared_with_id])

    __table_args__ = (
        db.UniqueConstraint(
            "document_id",
            "shared_with_id",
            name="unique_document_share",
        ),
    )


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    document_id = db.Column(db.Integer, nullable=True, default=None)
    username = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(30), nullable=False)
    details = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=utc_now)


# ---------------- AUDIT HELPER ----------------

def record_audit(action, details, document_id=None):
    db.session.add(AuditLog(
        user_id=current_user.id,
        document_id=document_id,
        username=current_user.username,
        action=action,
        details=details[:255],
        timestamp=utc_now(),
    ))
    db.session.commit()


# ---------------- LOGIN MANAGER ----------------

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


# ---------------- HELPERS ----------------

def allowed_file(filename):
    return (
        bool(filename)
        and "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def can_access_document(document):
    if document.owner_id == current_user.id:
        return True

    share = DocumentShare.query.filter_by(
        document_id=document.id,
        shared_with_id=current_user.id,
    ).first()

    return share is not None


# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if len(username) < 3:
            flash("Username must contain at least 3 characters.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return redirect(url_for("register"))

        if not email:
            flash("Email is required.")
            return redirect(url_for("register"))

        existing = User.query.filter(
            or_(User.username == username, User.email == email)
        ).first()

        if existing:
            flash("Username or email is already registered.")
            return redirect(url_for("register"))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("Registration failed")
            flash("Registration failed. Please try again.")
            return redirect(url_for("register"))

        flash("Account created successfully. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            # Do not create a persistent "remember me" cookie.
            login_user(user, remember=False, fresh=True)

            try:
                record_audit("LOGIN", "User logged in")
            except Exception:
                db.session.rollback()
                app.logger.exception("Login audit failed")

            return redirect(url_for("home"))

        flash("Invalid username or password.")

    return render_template("login.html")


# ---------------- LOGOUT ----------------

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    try:
        record_audit("LOGOUT", "User logged out")
    except Exception:
        db.session.rollback()
        app.logger.exception("Logout audit failed")

    logout_user()
    flash("You have logged out.")
    return redirect(url_for("home"))


# ---------------- DOCUMENTS AND UPLOAD ----------------

@app.route("/documents", methods=["GET", "POST"])
@login_required
def documents():
    if request.method == "POST":
        file = request.files.get("document")

        if not file or not file.filename:
            flash("Please choose a file.")
            return redirect(url_for("documents"))

        original_name = secure_filename(file.filename)

        if not original_name or not allowed_file(original_name):
            flash("File type not allowed.")
            return redirect(url_for("documents"))

        stored_name = (
            secrets.token_hex(16) + Path(original_name).suffix.lower()
        )
        destination = UPLOAD_DIR / stored_name

        try:
            file.save(destination)

            document = Document(
                original_name=original_name,
                stored_name=stored_name,
                owner_id=current_user.id,
            )
            db.session.add(document)
            db.session.flush()

            db.session.add(AuditLog(
                user_id=current_user.id,
                document_id=document.id,
                username=current_user.username,
                action="UPLOAD",
                details=f"Uploaded document: {original_name}"[:255],
                timestamp=utc_now(),
            ))
            db.session.commit()

        except Exception:
            db.session.rollback()

            if destination.exists():
                try:
                    destination.unlink()
                except OSError:
                    app.logger.exception("Failed to remove incomplete upload")

            app.logger.exception("Upload failed")
            flash("Upload failed. Please try again.")
            return redirect(url_for("documents"))

        flash("Document uploaded successfully.")
        return redirect(url_for("documents"))

    owned_documents = (
        Document.query
        .filter_by(owner_id=current_user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )

    shares = DocumentShare.query.filter_by(
        shared_with_id=current_user.id
    ).all()

    shared_documents = []
    for share in shares:
        document = db.session.get(Document, share.document_id)
        if document is not None:
            shared_documents.append(document)

    return render_template(
        "documents.html",
        documents=owned_documents,
        shared_documents=shared_documents,
    )


# ---------------- GRANT SHARING ----------------

@app.route("/documents/<int:document_id>/share", methods=["POST"])
@login_required
def share_document(document_id):
    document = db.session.get(Document, document_id)

    if document is None:
        abort(404)

    if document.owner_id != current_user.id:
        abort(403)

    username = request.form.get("username", "").strip()
    permission = request.form.get("permission", "read").lower()

    if permission not in {"read", "edit"}:
        flash("Invalid permission.")
        return redirect(url_for("documents"))

    recipient = User.query.filter_by(username=username).first()

    if recipient is None:
        flash("User not found.")
        return redirect(url_for("documents"))

    if recipient.id == current_user.id:
        flash("You already own this document.")
        return redirect(url_for("documents"))

    share = DocumentShare.query.filter_by(
        document_id=document.id,
        shared_with_id=recipient.id,
    ).first()

    try:
        if share:
            share.permission = permission
            share.owner_id = current_user.id
        else:
            share = DocumentShare(
                document_id=document.id,
                owner_id=current_user.id,
                shared_with_id=recipient.id,
                permission=permission,
            )
            db.session.add(share)

        db.session.add(AuditLog(
            user_id=current_user.id,
            document_id=document.id,
            username=current_user.username,
            action="SHARE",
            details=(
                f"Shared {document.original_name} with "
                f"{recipient.username} ({permission})"
            )[:255],
            timestamp=utc_now(),
        ))
        db.session.commit()

    except Exception:
        db.session.rollback()
        app.logger.exception("Share operation failed")
        flash("Could not share document.")
        return redirect(url_for("documents"))

    flash(f"Document shared with {recipient.username}.")
    return redirect(url_for("documents"))


# ---------------- REVOKE SHARING ----------------

@app.route(
    "/documents/<int:document_id>/revoke/<int:user_id>",
    methods=["POST"],
)
@login_required
def revoke_share(document_id, user_id):
    document = db.session.get(Document, document_id)

    if document is None:
        abort(404)

    if document.owner_id != current_user.id:
        abort(403)

    share = DocumentShare.query.filter_by(
        document_id=document.id,
        shared_with_id=user_id,
        owner_id=current_user.id,
    ).first()

    if share is None:
        flash("Sharing permission not found.")
        return redirect(url_for("documents"))

    recipient = db.session.get(User, user_id)
    recipient_name = recipient.username if recipient else str(user_id)

    try:
        db.session.add(AuditLog(
            user_id=current_user.id,
            document_id=document.id,
            username=current_user.username,
            action="REVOKE",
            details=(
                f"Revoked access to {document.original_name} "
                f"for {recipient_name}"
            )[:255],
            timestamp=utc_now(),
        ))
        db.session.delete(share)
        db.session.commit()

    except Exception:
        db.session.rollback()
        app.logger.exception("Revoke operation failed")
        flash("Could not revoke sharing permission.")
        return redirect(url_for("documents"))

    flash("Sharing permission revoked.")
    return redirect(url_for("documents"))


# ---------------- DOWNLOAD DOCUMENT ----------------

@app.route("/documents/<int:document_id>/download")
@login_required
def download_document(document_id):
    document = db.session.get(Document, document_id)

    if document is None:
        abort(404)

    if not can_access_document(document):
        try:
            record_audit(
                "ACCESS_DENIED",
                f"Denied access to document ID {document_id}",
                document_id=document_id,
            )
        except Exception:
            db.session.rollback()
            app.logger.exception("Denied-access audit failed")

        abort(403)

    file_path = UPLOAD_DIR / document.stored_name

    if not file_path.is_file():
        abort(404)

    try:
        record_audit(
            "DOWNLOAD",
            f"Downloaded document: {document.original_name}",
            document_id=document.id,
        )
    except Exception:
        db.session.rollback()
        app.logger.exception("Download audit failed")

    return send_from_directory(
        str(UPLOAD_DIR),
        document.stored_name,
        as_attachment=True,
        download_name=document.original_name,
    )


# ---------------- AUDIT TRAIL ----------------

@app.route("/audit")
@login_required
def audit_trail():
    logs = (
        AuditLog.query
        .filter_by(user_id=current_user.id)
        .order_by(AuditLog.timestamp.desc())
        .limit(200)
        .all()
    )

    return render_template("audit.html", logs=logs)


# ---------------- ERROR HANDLING ----------------

@app.errorhandler(413)
def file_too_large(error):
    flash("File is too large. Maximum size is 5 MB.")
    return redirect(url_for("documents"))


# ---------------- DATABASE INITIALIZATION ----------------

with app.app_context():
    db.create_all()


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":
    app.run(debug=False)
