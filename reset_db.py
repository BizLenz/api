# reset_db.py (최종 CASCADE 버전 - 빌드 오류 수정)

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# 'src' 폴더를 파이썬 경로에 동적으로 추가하여 'from app...' import가 가능하게 함
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(project_root, 'src'))

# 데이터베이스 연결 URL 생성
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# 데이터베이스 URL이 올바르게 생성되었는지 확인
if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    print("❌ .env 파일에 데이터베이스 연결 정보가 올바르게 설정되지 않았습니다.")
    sys.exit(1)

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 데이터베이스 엔진 생성
engine = create_engine(DATABASE_URL)

# 운영 환경(Production)일 경우, 사용자에게 재확인 절차를 거침
if os.getenv("ENV") == "production":
    print("🚨 경고: 현재 운영 환경(production)으로 설정되어 있습니다.")
    print("이 스크립트를 실행하면 데이터베이스의 모든 데이터가 영구적으로 삭제됩니다.")
    
    confirm = input("정말로 데이터베이스를 초기화하려면 'YES'를 입력하세요: ")
    
    if confirm != "YES":
        print("작업이 취소되었습니다.")
        sys.exit(0)

try:
    with engine.connect() as connection:
        # 스키마 변경을 위해 이전 트랜잭션을 커밋하고, 새 트랜잭션을 시작합니다.
        connection.commit()
        print("🔗 데이터베이스에 연결되었습니다. 완전 초기화를 시작합니다...")

        # 모든 의존성 객체와 함께 public 스키마를 삭제하고, 다시 생성합니다.
        # 이것이 모든 것을 초기화하는 가장 확실한 방법입니다.
        connection.execute(text("DROP SCHEMA public CASCADE;"))
        print("✔️ public 스키마 및 모든 의존 객체 삭제 완료.")
        
        connection.execute(text("CREATE SCHEMA public;"))
        print("✔️ public 스키마 재생성 완료.")

        # 새 스키마에 기본 권한을 복원합니다.
        connection.execute(text(f"GRANT ALL ON SCHEMA public TO {DB_USER};"))
        connection.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        print("✔️ 스키마 권한 복원 완료.")
        
        # 스키마 변경사항을 완전히 적용하기 위해 커밋합니다.
        connection.commit()
        
        print("\n✅ 데이터베이스가 완전히 초기화되었습니다.")
        print("다음 명령어를 실행하여 DB를 다시 만드세요:")
        print("  alembic upgrade head")

except Exception as e:
    print(f"❌ 오류가 발생했습니다: {e}")
    sys.exit(1)