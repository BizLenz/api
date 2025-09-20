from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.models import User


def get_or_create_user(db: Session, cognito_sub: str) -> type[User] | User:
    """
    Find user using the given Cognito sub(user_id), create if not found
    """
    user = db.query(User).filter(User.id == cognito_sub).first()
    if user:
        return user

    # TODO: Remove this logic when RDS is ready
    # User does not exist, create a new one
    new_user = User(
        id=cognito_sub,  # Set the primary key 'id' to the Cognito sub
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)  # Refresh to load default values
    return new_user
