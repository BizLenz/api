from __future__ import annotations
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.models import AnalysisResult, AnalysisJob, BusinessPlan


def create_analysis_result(
    db: Session,
    *,
    analysis_job_id: int,
    evaluation_type: str,
    score: Optional[float],
    summary: Optional[str],
    details: Dict[str, Any],
) -> AnalysisResult:
    """
    INSERT new record into AnalysisResult table.
    - flush/commit and refresh to fill the PK/timestamp.
    """
    obj = AnalysisResult(
        analysis_job_id=analysis_job_id,
        evaluation_type=evaluation_type,
        score=score,
        summary=summary,
        details=details,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    # Update business_plans.latest_job_id
    job = (
        db.query(AnalysisJob)
        .filter(AnalysisJob.id == analysis_job_id)
        .first()
    )
    if job:
        plan = (
            db.query(BusinessPlan)
            .filter(BusinessPlan.id == job.plan_id)
            .first()
        )
        if plan:
            plan.latest_job_id = analysis_job_id
            db.commit()
            db.refresh(plan)

    return obj


def get_analysis_result(db: Session, *, plan_id: int) -> Optional[AnalysisResult]:
    """
    Get the latest AnalysisResult associated with the latest AnalysisJob for a specific plan_id.

    - db (Session): Database session
    - plan_id (int): ID of the plan (business plan) to query
    """

    latest_job_id = db.execute(
        select(AnalysisJob.id)
        .where(AnalysisJob.plan_id == plan_id)
        .order_by(AnalysisJob.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest_job_id is None:
        return None

    return (
        db.query(AnalysisResult)
        .filter(AnalysisResult.analysis_job_id == latest_job_id)
        .first()
    )
