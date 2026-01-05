from fastapi import APIRouter, Depends, HTTPException, Query 
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.db.db_postgres import get_db
from backend.app.db.models_user import User
from backend.app.core.admin_guard import admin_required

from pydantic import BaseModel
from typing import Optional


router = APIRouter(
    prefix="/admin/users",
    tags=["Admin Users"]
)


@router.get("")
def list_users(
    db: Session = Depends(get_db),
    _=Depends(admin_required)
):
    """
    Mỗi dòng = 1 conversation của user
    Có title_character (tiêu đề đoạn chat)
    """
    rows = db.execute(text("""
        SELECT 
            u.id               AS user_id,
            u.username,
            u.role,
            u.create_at        AS user_created_at,

            c.id               AS conversation_id,
            c.title           AS title_character,
            c.created_at       AS conversation_created_at
        FROM users u
        LEFT JOIN conversations c
            ON u.id = c.user_id
        ORDER BY u.create_at DESC, c.created_at DESC
    """)).fetchall()

    return [
        {
            "user_id": r.user_id,
            "username": r.username,
            "role": r.role,
            "user_created_at": r.user_created_at,
            "conversation_id": r.conversation_id,
            "title_character": r.title_character,
            "conversation_created_at": r.conversation_created_at
        }
        for r in rows
    ]


# ================== UPDATE ROLE ==================

class AdminUpdateUser(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None


@router.put("/{user_id}")
def update_user(
    user_id: int,
    data: AdminUpdateUser,
    db: Session = Depends(get_db),
    _=Depends(admin_required)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    if data.username is not None:
        user.username = data.username

    if data.password:
        user.password = data.password
        user.password_hash = data.password  

    if data.role:
        if data.role not in ["user", "admin"]:
            raise HTTPException(400, "Invalid role")
        user.role = data.role

    db.commit()

    return {"message": "User updated successfully"}



# ================== DELETE USER ==================
@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(admin_required)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Xoá messages
    db.execute(
        text("""
            DELETE FROM messages
            WHERE conversation_id IN (
                SELECT id FROM conversations WHERE user_id = :uid
            )
        """),
        {"uid": user_id}
    )

    # Xoá conversations
    db.execute(
        text("DELETE FROM conversations WHERE user_id = :uid"),
        {"uid": user_id}
    )

    # Xoá user
    db.delete(user)
    db.commit()

    return {"message": "User deleted"}


# ================== GET USER CONVERSATIONS ==================
@router.get("/{user_id}/conversations")
def get_user_conversations(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(admin_required)
):
    rows = db.execute(
        text("""
            SELECT 
                id,
                title_character,
                created_at
            FROM conversations
            WHERE user_id = :uid
            ORDER BY created_at DESC
        """),
        {"uid": user_id}
    ).fetchall()

    return [
        {
            "conversation_id": r.id,
            "title_character": r.title_character,
            "created_at": r.created_at
        }
        for r in rows
    ]


# ================== STORED PROCEDURE (OPTIONAL) ==================
@router.get("/full")
def admin_users_full_view(
    db: Session = Depends(get_db),
    _=Depends(admin_required)
):
    """
    Dùng stored procedure:
    get_admin_users_conversations()
    """
    result = db.execute(
        text("SELECT * FROM get_admin_users_conversations()")
    )
    return [dict(row._mapping) for row in result]
