import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(project_root, "src"))

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    print("Database connection info in .env is not properly configured.")
    sys.exit(1)

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

if os.getenv("ENV") == "production":
    print("WARNING: Currently set to production environment.")
    print("Running this script will permanently delete all database data.")
    confirm = input("Type 'YES' to reset the database: ")
    if confirm != "YES":
        print("Operation cancelled.")
        sys.exit(0)

try:
    with engine.connect() as connection:
        connection.commit()
        print("Connected. Starting full reset...")

        connection.execute(text("DROP SCHEMA public CASCADE;"))
        connection.execute(text("CREATE SCHEMA public;"))
        connection.execute(text(f"GRANT ALL ON SCHEMA public TO {DB_USER};"))
        connection.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        connection.commit()

        print("Database reset complete. Run: alembic upgrade head")

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
