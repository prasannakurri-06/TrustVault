
import sqlite3
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "trustvault.db"
BACKUP_PATH = BASE_DIR / "trustvault_before_migration.db"

if not DB_PATH.exists():
    raise SystemExit(f"Database not found: {DB_PATH}")

# Create a backup before making any changes.
if not BACKUP_PATH.exists():
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print("Backup created:", BACKUP_PATH)
else:
    print("Backup already exists:", BACKUP_PATH)

connection = sqlite3.connect(DB_PATH)

try:
    connection.execute("PRAGMA foreign_keys = OFF")

    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(audit_log)")
    }

    if not columns:
        raise RuntimeError(
            "audit_log table was not found. Database was not migrated."
        )

    print("Current audit_log columns:", sorted(columns))

    if "document_id" not in columns:
        print("document_id column is already absent; no change needed.")

    else:
        connection.execute("BEGIN")

        connection.execute("""
            CREATE TABLE audit_log_new (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                document_id INTEGER NULL,
                action VARCHAR(30) NOT NULL,
                timestamp DATETIME NOT NULL,
                username VARCHAR(80) NOT NULL DEFAULT 'Unknown',
                details VARCHAR(255) NOT NULL DEFAULT ''
            )
        """)

        expressions = {
            "id": "id",
            "user_id": "user_id",
            "document_id": "document_id",
            "action": "action",
            "timestamp": "timestamp",
            "username": (
                "username" if "username" in columns else "'Unknown'"
            ),
            "details": (
                "details" if "details" in columns else "''"
            ),
        }

        target_columns = list(expressions.keys())
        column_sql = ", ".join(target_columns)
        value_sql = ", ".join(
            expressions[column] for column in target_columns
        )

        connection.execute(
            f"""
            INSERT INTO audit_log_new ({column_sql})
            SELECT {value_sql}
            FROM audit_log
            """
        )

        connection.execute("DROP TABLE audit_log")
        connection.execute(
            "ALTER TABLE audit_log_new RENAME TO audit_log"
        )

        connection.commit()
        print("Migration successful!")

except Exception as error:
    connection.rollback()
    print("Migration failed:", error)
    raise

finally:
    connection.close()
