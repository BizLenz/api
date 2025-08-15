# src/app/crud/user.py
from sqlalchemy.orm import Session
from app.models import User


def create_user(db: Session,*, username: str, password_hash: str, email: str | None, phone_number: str | None, address: str | None) -> User:
    user = User(
        username=username,
        password_hash=password_hash,
        email=email,
        phone_number=phone_number,
        address=address,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user



