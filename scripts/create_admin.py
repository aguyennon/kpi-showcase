from getpass import getpass
from app.auth import hash_password
from app.db import get_connection

username = input("Username: ").strip()

password = getpass("Password: ")
confirm = getpass("Confirm password: ")

if password != confirm:
    raise SystemExit("Passwords don't match - nothing was saved.")

if len(password) < 12:
    raise SystemExit("Use at least 12 characters - nothing was saved.")

with get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO dbo.AdminUser (Username, PasswordHash) VALUES (?, ?)",
        username,
        hash_password(password),
    )
    conn.commit()

print(f"Admin '{username}' has been created.")