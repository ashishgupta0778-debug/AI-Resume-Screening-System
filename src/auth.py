import secrets
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from src.db import get_db


def create_session(user_id: int, email: str, duration_hours: int = 24) -> str:
    token = secrets.token_hex(32)
    expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO sessions (token, user_id, email, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (token, user_id, email, expires_at.strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()
    return token


def validate_session(token: str) -> dict | None:
    if not token:
        return None
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.token, s.user_id, s.email, s.expires_at, u.role
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ?
        """,
        (token,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
        
    try:
        expires_at = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.utcnow() > expires_at:
            delete_session(token)
            return None
    except Exception:
        pass
        
    return {
        "user_id": row["user_id"],
        "email": row["email"],
        "role": row["role"]
    }


def delete_session(token: str) -> bool:
    if not token:
        return False
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.headers.get("X-Session-Token")
    if not token:
        token = request.query_params.get("token")
        
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing. Please sign in."
        )
        
    user = validate_session(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please sign in again."
        )
        
    return user
