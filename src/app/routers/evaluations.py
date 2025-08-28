# src/app/routers/evaluations.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime, timezone

from app.database import get_db
from app.models import AnalysisJob, AnalysisResult, BusinessPlan
from app.schemas.evaluation import EvaluationRequest, EvaluationResponse
from app.core.security import require_scope, get_claims

# 라우터 생성 (자동 등록 시스템용 - 변수명 router로 통일)
router = APIRouter(dependencies=[Depends(require_scope("openid"))])

def _utcnow():
   """UTC 현재 시간 반환"""
   return datetime.now(timezone.utc)

@router.post("/save", response_model=dict)
def save_evaluation_result(
   evaluation_data: EvaluationResponse,
   plan_id: int,
   db: Session = Depends(get_db),
   claims: Dict[str, Any] = Depends(get_claims),
):
   """
   평가 결과를 DB에 저장하는 엔드포인트
   - evaluation_data: 평가 완료된 EvaluationResponse 객체
   - plan_id: 평가 대상 사업계획서 ID
   """
   try:
       # 1. BusinessPlan 존재 확인
       business_plan = db.query(BusinessPlan).filter(BusinessPlan.id == plan_id).first()
       if not business_plan:
           raise HTTPException(status_code=404, detail="Business plan not found")

       # 2. AnalysisJob 생성 (작업 정보)
       analysis_job = AnalysisJob(
           plan_id=plan_id,
           job_type="evaluation",  # 평가 작업 타입
           status="completed",     # 이미 평가 완료된 상태
           created_at=_utcnow(),
           completed_at=_utcnow()
       )
       db.add(analysis_job)
       db.flush()  # analysis_job.id 확보

       # 3. AnalysisResult 생성 (평가 결과)
       analysis_result = AnalysisResult(
           analysis_job_id=analysis_job.id,
           evaluation_type="overall",  # 종합 평가
           score=evaluation_data.total_score,
           summary=f"총점: {evaluation_data.total_score}점",
           details=evaluation_data.model_dump(exclude_none=True),  # EvaluationResponse 전체를 JSONB로 저장
           created_at=_utcnow()
       )
       db.add(analysis_result)

       # 4. BusinessPlan의 latest_job_id 업데이트
       business_plan.latest_job_id = analysis_job.id
       business_plan.status = "completed"
       
       db.commit()

       return {
           "message": "Evaluation result saved successfully",
           "analysis_job_id": analysis_job.id,
           "analysis_result_id": analysis_result.id,
           "total_score": evaluation_data.total_score
       }

   except Exception as e:
       db.rollback()
       raise HTTPException(status_code=500, detail=f"Error saving evaluation result: {str(e)}")

@router.get("/{analysis_job_id}", response_model=dict)
def get_evaluation_result(
   analysis_job_id: int,
   db: Session = Depends(get_db),
   claims: Dict[str, Any] = Depends(get_claims),
):
   """
   저장된 평가 결과 조회
   - analysis_job_id: 조회할 분석 작업 ID
   """
   try:
       # AnalysisJob과 연관된 AnalysisResult 조회
       analysis_result = (
           db.query(AnalysisResult)
           .filter(AnalysisResult.analysis_job_id == analysis_job_id)
           .first()
       )
       
       if not analysis_result:
           raise HTTPException(status_code=404, detail="Evaluation result not found")

       return {
           "analysis_job_id": analysis_job_id,
           "analysis_result_id": analysis_result.id,
           "evaluation_type": analysis_result.evaluation_type,
           "score": analysis_result.score,
           "summary": analysis_result.summary,
           "details": analysis_result.details,  # 전체 EvaluationResponse JSONB
           "created_at": analysis_result.created_at.isoformat()
       }

   except Exception as e:
       raise HTTPException(status_code=500, detail=f"Error retrieving evaluation result: {str(e)}")

@router.get("/latest/{plan_id}", response_model=dict)
def get_latest_evaluation(
   plan_id: int,
   db: Session = Depends(get_db),
   claims: Dict[str, Any] = Depends(get_claims),
):
   """
   특정 사업계획서의 최신 평가 결과 조회
   - plan_id: 사업계획서 ID
   """
   try:
       # BusinessPlan의 latest_job_id를 통해 최신 결과 조회
       business_plan = db.query(BusinessPlan).filter(BusinessPlan.id == plan_id).first()
       if not business_plan or not business_plan.latest_job_id:
           raise HTTPException(status_code=404, detail="No evaluation found for this business plan")

       analysis_result = (
           db.query(AnalysisResult)
           .filter(AnalysisResult.analysis_job_id == business_plan.latest_job_id)
           .first()
       )

       if not analysis_result:
           raise HTTPException(status_code=404, detail="Latest evaluation result not found")

       return {
           "plan_id": plan_id,
           "analysis_job_id": business_plan.latest_job_id,
           "analysis_result_id": analysis_result.id,
           "evaluation_type": analysis_result.evaluation_type,
           "score": analysis_result.score,
           "summary": analysis_result.summary,
           "details": analysis_result.details,
           "created_at": analysis_result.created_at.isoformat()
       }

   except Exception as e:
       raise HTTPException(status_code=500, detail=f"Error retrieving latest evaluation: {str(e)}")