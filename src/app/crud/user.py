from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.models import User


def get_or_create_user(db: Session, user_id: str) -> User:
    """
    Find user by OIDC sub claim
    Create if not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        return user

    new_user = User(
        id=user_id,  # Set the primary key 'id' to the OIDC sub claim
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
