# for the admin view

from email.policy import HTTP
import time
import bcrypt
from fastapi import HTTPException, Request
from app.db import get_connection

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt())

MAX_FAILURES = 5

WINDOW_SECONDS = 15 * 60 

_failures: dict[str, list[float]] = {}


def _recent_failures(username: str) -> str:
    cutoff = time.monotonic() - WINDOW_SECONDS
    recent = [t for t in _failures.get(username, []) if t > cutoff]
    _failures[username] = recent
    return recent


def is_locked_out(username: str) -> bool:
    return len(_recent_failures(username)) >= MAX_FAILURES


def _record_failure(username: str) -> None:
    _recent_failures(username).append(time.monotonic())


async def verify_admin_login(username: str, password: str) -> bool:
    if is_locked_out(username):
        return False

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT PasswordHash FROM dbo.AdminUser WHERE Username = ? AND IsActive = 1",
            username,
        )
        row = cursor.fetchone()
        

    if row is None:
        bcrypt.checkpw(password.encode(), _DUMMY_HASH)
        _record_failure(username)
        return False

    _failures.pop(username, None)
    return True


def require_admin(request: Request) -> str:
    username = request.session.get("admin")
    if not username:
        raise HTTPException(status_code=401, detail="Not signed in")
    return username









