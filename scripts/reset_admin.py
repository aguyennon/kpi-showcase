"""Resets an existing admin's password.

Same hashing as create_admin — the old password isn't recoverable, so this
overwrites it with a new hash rather than revealing anything."""

from getpass import getpass

from app.auth import hash_password
from app.db import get_connection

username = input("Username: ").strip()
password = getpass("New password: ")
confirm = getpass("Confirm: ")

if password != confirm:
    raise SystemExit("Passwords don't match — nothing changed.")

if len(password) < 12:
    raise SystemExit("Use at least 12 characters — nothing changed.")

with get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE dbo.AdminUser SET PasswordHash = ? WHERE Username = ?",
        hash_password(password),
        username,
    )
    if cursor.rowcount == 0:
        raise SystemExit(f"No admin named '{username}' — nothing changed.")
    conn.commit()

print(f"New password hash: {hash_password(password)}")
print(f"Password reset for '{username}'.")