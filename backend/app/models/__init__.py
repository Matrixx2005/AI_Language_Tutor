"""Import mọi model ở đây để Base.metadata đầy đủ (Alembic autogenerate dùng file này)."""
from app.models.chat import ChatMessageRow, ChatSession
from app.models.exercise import ErrorEvent, Exercise, ExerciseAttempt
from app.models.learner_profile import LearnerProfile
from app.models.placement import PlacementResult, Question
from app.models.user import User

__all__ = ["ChatMessageRow", "ChatSession", "ErrorEvent", "Exercise", "ExerciseAttempt", "LearnerProfile", "PlacementResult", "Question", "User"]
