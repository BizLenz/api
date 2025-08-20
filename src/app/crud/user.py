# src/app/crud/user.py
from sqlalchemy.orm import Session
from app.models.models import User
from sqlalchemy import update 
from sqlalchemy.exc import IntegrityError 
from app.models.models import User
from typing import Optional

def get_by_sub(db: Session, cognito_sub: str) -> User | None:
    """
    Cognito의 sub(고유 식별자)를 사용하여 사용자를 조회합니다.
    Args:
        db (Session): FastAPI의 Depends를 통해 주입된 DB 세션 객체입니다.
        cognito_sub (str): 조회할 사용자의 Cognito sub 값입니다.
    Returns:
        User | None: 사용자를 찾으면 User 객체를, 찾지 못하면 None을 반환합니다.
    """
    # users 테이블에서 cognito_sub 컬럼이 일치하는 첫 번째 레코드를 찾습니다.
    return db.query(User).filter(User.cognito_sub == cognito_sub).one_or_none()

def create_if_not_exists(db:Session, cognito_sub:str)-> User:
    """
    사용자가 존재하지 않으면 새로 생성하고, 존재하면 기존 객체를 반환합니다. (멱등성 보장)
    멱등성: 여러 번 호출해도 결과가 동일하게 유지되는 성질입니다.

    Args:
        db (Session): DB 세션 객체입니다.
        cognito_sub (str): 생성할 사용자의 Cognito sub 값입니다.

    Returns:
        User: 생성되었거나 이미 존재하던 User 객체를 반환합니다.
    """
    # 먼저 해당 sub로 사용자가 있는지 확인합니다.
    inst = get_by_sub(db, cognito_sub)
    if inst:
        # 이미 존재하면, 추가 작업 없이 바로 반환합니다.
        return inst

    # 존재하지 않으면, 새로운 User 객체를 생성합니다.
    inst = User(cognito_sub=cognito_sub)
    db.add(inst)

    try:
         # DB에 실제 저장을 시도합니다. flush를 통해 id 등 DB에서 자동 생성되는 값을 받아옵니다.
        db.flush()
    except IntegrityError:
        db.rollback()
        inst = get_by_sub(db,cognito_sub)

    return inst


def increment_token_usage(db: Session, cognito_sub: str, inc: int) -> Optional[User]:
    """
    사용자의 누적 토큰 사용량을 원자적으로(atomically) 증가시킵니다.
    원자적 연산: 여러 단계로 구성된 작업이 중간에 중단되지 않고 한 번에 실행되는 것을 보장합니다.

    Args:
        db (Session): DB 세션 객체입니다.
        cognito_sub (str): 토큰 사용량을 증가시킬 사용자의 Cognito sub입니다.
        inc (int): 증가시킬 토큰의 양입니다.

    Returns:
        User | None: 업데이트 성공 시 최신 User 객체를, 대상 사용자가 없으면 None을 반환합니다.
    """
    # SQLAlchemy Core의 update 표현식을 사용하여 원자적 업데이트 SQL을 생성합니다.
    # "UPDATE users SET total_token_usage = total_token_usage + :inc WHERE cognito_sub = :sub"
    # 이렇게 해야 여러 요청이 동시에 들어와도 정확한 값으로 업데이트됩니다.
    stmt = (
        update(User)
        .where(User.cognito_sub == cognito_sub)
        .values(total_token_usage=User.total_token_usage + inc)
        .returning(User.id)  # 업데이트된 레코드의 id를 반환받습니다.
    )
    result = db.execute(stmt)
    updated_row = result.fetchone() # 업데이트된 행을 가져옵니다.
    if not updated_row:
        return None
    return get_by_sub(db, cognito_sub)

