# src/app/crud/user.py

from sqlalchemy.orm import Session
from app.models import user as models
from app.schemas import user as schemas
from app.core.security import get_password_hash, verify_password


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    hashed_pw = get_password_hash(user_in.password)
    db_user = models.User(email=user_in.email, hashed_password=hashed_pw)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def verify_user(db: Session, user_in: schemas.UserLogin) -> models.User | None:
    db_user = get_user_by_email(db, user_in.email)
    if not db_user:
        return None
    if not verify_password(user_in.password, db_user.hashed_password):
        return None
    return db_user
