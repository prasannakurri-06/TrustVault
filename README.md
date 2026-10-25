# TrustVault — Secure Document Sharing with a Real Audit Trail

## Project Overview

TrustVault is a secure document-sharing web application built using Python Flask. It allows registered users to upload and download their own documents while maintaining an audit trail of important activities.

## Features

- User registration and login
- Secure password hashing
- Document upload and download
- Owner-based document access control
- File type validation
- Maximum upload size of 5 MB
- Audit trail for login, logout, upload, download, and denied-access events
- Document names and timestamps in audit logs
- SQLite database for application data
- Responsive, user-friendly interface

## Technologies Used

- **Frontend:** HTML, CSS
- **Backend:** Python, Flask
- **Database:** SQLite
- **ORM:** Flask-SQLAlchemy
- **Authentication:** Flask-Login
- **Password Security:** Werkzeug password hashing utilities

## Project Structure

```text
TrustVault/
├── app.py
├── requirements.txt
├── migrate_audit.py
├── static/
│   └── style.css
├── templates/
│   ├── index.html
│   ├── register.html
│   ├── login.html
│   ├── documents.html
│   └── audit.html
└── uploads/
```

The SQLite database and local secret-key file are created or maintained locally and should not be committed if they contain private data or credentials.

## Installation and Setup

### 1. Open the project

Open the TrustVault project folder in Visual Studio Code or a terminal.

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

**Windows:**

```bash
.venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
python app.py
```

### 6. Open the application

Visit the following URL in your browser:

```text
http://127.0.0.1:5000
```

Register an account, log in, upload a document, download it, and check the audit trail.

## Supported File Types

- PDF
- TXT
- PNG
- JPG
- JPEG
- DOCX

**Maximum upload size:** 5 MB.

## Security Notes

TrustVault implements password hashing, authenticated access, owner-based document download authorization, randomized stored filenames, file extension validation, upload size limits, and audit logging.

This project is a development prototype and has not been independently security-audited. Additional protections, including CSRF protection, stronger file-content validation, production-grade configuration, and tamper-resistant audit logging, should be considered before production deployment.

## Future Enhancements

- Share documents with selected users
- Expiring download links
- Document encryption
- Advanced access permissions
- Audit log export
- Secure cloud deployment

## Author

Developed as a fresher hiring challenge project.
