"""Kiểm tra ràng buộc thật trong PostgreSQL (DB test, mỗi test rollback)."""
import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import LearnerProfile, User


def add_user(session: Session, email: str = "learner@example.com") -> User:
    user = User(email=email, password_hash="argon2-hash-placeholder")
    session.add(user)
    session.flush()
    return user


def test_profile_gets_erd_defaults_from_database(db_session: Session):
    user = add_user(db_session)
    db_session.add(LearnerProfile(user_id=user.user_id))
    db_session.flush()
    db_session.expire_all()

    profile = db_session.scalars(select(LearnerProfile)).one()
    assert (profile.language_code, profile.current_level_code, profile.native_language_code) == (
        "en",
        "A1",
        "vi",
    )
    assert profile.learning_goal is None
    assert profile.updated_at is not None
    assert profile.user.created_at is not None


def test_duplicate_email_is_rejected(db_session: Session):
    add_user(db_session)
    with pytest.raises(IntegrityError, match="uq_users_email"), db_session.begin_nested():
        add_user(db_session)


@pytest.mark.parametrize("email", ["Learner@Example.com", " learner@example.com"])
def test_unnormalized_email_is_rejected(db_session: Session, email: str):
    with pytest.raises(IntegrityError, match="ck_users_email_normalized"), db_session.begin_nested():
        add_user(db_session, email)


def test_deleting_user_with_profile_is_restricted(db_session: Session):
    user = add_user(db_session)
    db_session.add(LearnerProfile(user_id=user.user_id))
    db_session.flush()

    with pytest.raises(IntegrityError, match="fk_learner_profiles_user_id_users"):
        with db_session.begin_nested():
            db_session.execute(delete(User).where(User.user_id == user.user_id))


def test_profile_requires_existing_user(db_session: Session):
    import uuid

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(LearnerProfile(user_id=uuid.uuid4()))
        db_session.flush()
