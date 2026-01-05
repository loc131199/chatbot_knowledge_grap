from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.db.models_user import User
from backend.app.api.routes.auth import get_current_user
from backend.app.db.db_postgres import get_db
from backend.app.schemas.chat import MessageRequest, MessageResponse
from backend.app.services.chatbot_service import ChatbotLogic
from backend.app.core.jwt_handler import verify_token
from sqlalchemy import text

print("🔥 CHAT ROUTER LOADED – SAFE MODE")

router = APIRouter(prefix="/chat", tags=["Chat"])

_chatbot = ChatbotLogic()

@router.post("", response_model=MessageResponse)
async def chat_endpoint(
    req: MessageRequest,
    token_data=Depends(verify_token)
):
    reply = _chatbot.chat(req.message)
    return MessageResponse(reply=reply)

@router.get("/conversations")
def get_conversations(
    token_payload=Depends(verify_token),
    db: Session = Depends(get_db)
):
    user_id = int(token_payload["sub"])
    rows = db.execute(
        text("""
            SELECT id, title, created_at
            FROM conversations
            WHERE user_id = :uid
        """),
        {"uid": user_id}
    ).fetchall()

    conversations =[]
    for r in rows:
        conversations.append({
            "id": r.id,
            "title": r.title,
            "created_at": r.created_at
        })
    return conversations

@router.get("/chat/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = db.execute(
        text(
        """
        SELECT id
        FROM conversations
        WHERE id = :cid AND user_id = :uid
        """),
        {"cid": conversation_id, "uid": current_user.id}
    ).fetchone()

    if not conv:
        raise HTTPException(status_code=403, detail="Forbidden")

    rows = db.execute(
        text("""
        SELECT role, content, created_at
        FROM messages
        WHERE conversation_id = :cid
        ORDER BY created_at ASC
        """),
        {"cid": conversation_id}
    ).fetchall()

    messages = []
    for r in rows:
        messages.append({
            "role": r.role,
            "content": r.content,
            "created_at": r.created_at
        })

    return messages
