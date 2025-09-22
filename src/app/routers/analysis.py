# file: app/routers/analysis.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import BusinessPlan, AnalysisResult
from app.core.security import get_claims
from app.routers.files import get_current_user_id

analysis = APIRouter(prefix="/analysis", tags=["analysis"])


# 유저가 관련 업종/시장상황/전문적 의견 데이터 요청
@analysis.get("/industry-data", response_model=Dict[str, Any])
def get_industry_data(
    file_id: int = Query(..., description="사업계획서 파일 ID"),
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
):
    """
    특정 사업계획서(file_id)에 연결된 최신 industry/market 분석 결과 조회
    - 유저 본인의 파일만 접근 가능
    - 데이터 없으면 404 반환
    """
    user_id = get_current_user_id(claims)

    business_plan = (
        db.query(BusinessPlan)
        .filter(BusinessPlan.id == file_id, BusinessPlan.user_id == user_id)
        .first()
    )
    if not business_plan:
        raise HTTPException(status_code=404, detail="File not found or access denied")

    if not business_plan.latest_job_id:
        raise HTTPException(status_code=404, detail="No analysis job found")

    results = (
        db.query(AnalysisResult)
        .filter(
            AnalysisResult.analysis_job_id == business_plan.latest_job_id,
            AnalysisResult.evaluation_type.in_(["industry", "market"]),
        )
        .all()
    )
    if not results:
        raise HTTPException(
            status_code=404, detail="Industry/market analysis not found"
        )

    industry_trends, market_conditions = None, None
    sources = []
    for r in results:
        if r.evaluation_type == "industry":
            industry_trends = r.details.get("industry_trends")
            if "source" in r.details:
                sources.append(r.details["source"])
        elif r.evaluation_type == "market":
            market_conditions = r.details.get("market_conditions")
            if "source" in r.details:
                sources.append(r.details["source"])

    return {
        "status": "success",
        "data": {
            "industry_trends": industry_trends,
            "market_conditions": market_conditions,
        },
        "sources": list(set(sources)),
    }


# 유저가 분석 기록 삭제 요청
@analysis.post("/records/{action}")
def manage_analysis_record(
    action: str,
    file_id: int,
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
):
    """
    파일별 분석 기록 삭제
    API 명세서: POST /api/analysis/records/{action}
    """
    user_id = get_current_user_id(claims)

    business_plan = (
        db.query(BusinessPlan)
        .filter(BusinessPlan.id == file_id, BusinessPlan.user_id == user_id)
        .first()
    )
    if not business_plan:
        raise HTTPException(status_code=404, detail="File not found or access denied")

    if not business_plan.latest_job_id:
        raise HTTPException(status_code=404, detail="No analysis job found")

    if action == "delete":
        try:
            # 최신 AnalysisResult 삭제
            record = (
                db.query(AnalysisResult)
                .filter(AnalysisResult.analysis_job_id == business_plan.latest_job_id)
                .order_by(AnalysisResult.created_at.desc())
                .first()
            )
            if record:
                db.delete(record)
                db.commit()
                message = "Analysis record deleted successfully"
            else:
                raise HTTPException(status_code=404, detail="No analysis record found")

        except HTTPException as e:
            db.rollback()
            raise e
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"Error deleting analysis record: {str(e)}"
            )
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    return {"status": "success", "message": message}
