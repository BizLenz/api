from sqlalchemy.orm import Session
from app.models.models import BusinessPlan
from app.schemas.file_schemas import FileMetadataSaveRequest


def create_business_plan(
    db: Session, business_plan_data: FileMetadataSaveRequest, user_id: str
):
    """
    Upload to S3 then save BusinessPlan metadata in the DB.
    """
    db_business_plan = BusinessPlan(
        user_id=user_id,
        file_name=business_plan_data.file_name,
        file_path=business_plan_data.s3_key,
        file_size=business_plan_data.file_size,
        mime_type=business_plan_data.mime_type,
    )

    db.add(db_business_plan)
    db.commit()
    db.refresh(db_business_plan)
    return db_business_plan