from sqlalchemy.orm import Session
from app.models.models import User
from app.schemas.file_schemas import FileUploadRequest

def create_file_metadata(db: Session, metadata: FileUploadRequest):
    db_file = User(**metadata.dict())
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file
    