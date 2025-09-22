from __future__ import annotations
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.models import AnalysisResult


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
    AnalysisResults 테이블에 새 레코드(행)를 INSERT 합니다.
    - flush/commit 후 refresh로 생성된 PK/타임스탬프를 채워 반환합니다.
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
    return obj


def get_analysis_result(db: Session, *, result_id: int) -> Optional[AnalysisResult]:
    """
    AnalysisResults 테이블에서 ID로 단일 레코드를 조회합니다.
    """
    return db.query(AnalysisResult).filter(AnalysisResult.id == result_id).first()
