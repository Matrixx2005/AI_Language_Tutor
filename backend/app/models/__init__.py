"""Import mọi model ở đây để Base.metadata đầy đủ (Alembic autogenerate dùng file này)."""
from app.models.chat import ChatMessageRow, ChatSession
from app.models.learner_profile import LearnerProfile
from app.models.user import User

__all__ = ["ChatMessageRow", "ChatSession", "LearnerProfile", "User"]
