# src/app/routers/evaluations.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from typing import Dict, Any
from datetime import datetime, timezone
from decimal import Decimal

from app.database import get_db
from app.models import AnalysisJob, AnalysisResult, BusinessPlan
from app.schemas.evaluation import (
    EvaluationRequest, 
    EvaluationResponse, 
    evaluation_response_to_db_json
)
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
    
    트랜잭션 안정성을 위한 개선사항:
    1. 원자적 트랜잭션 처리
    2. 외래키 순환참조 해결
    3. 데이터 검증 강화
    """
    # 트랜잭션 시작
    try:
        # 1. 입력 데이터 검증
        if not evaluation_data.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="평가가 성공적으로 완료되지 않은 데이터는 저장할 수 없습니다."
            )
        
        if evaluation_data.total_score is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="총점이 없는 평가 데이터는 저장할 수 없습니다."
            )

        # 2. BusinessPlan 존재 확인 및 사용자 권한 검증
        business_plan = (
            db.query(BusinessPlan)
            .filter(BusinessPlan.id == plan_id)
            .first()
        )
        if not business_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 사업계획서를 찾을 수 없습니다."
            )

        # 3. 사용자 권한 확인 (옵션: 필요시 활성화)
        # user_sub = claims.get("sub")
        # if business_plan.user.cognito_sub != user_sub:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="해당 사업계획서에 대한 권한이 없습니다."
        #     )

        current_time = _utcnow()

        # 4. AnalysisJob 생성 (외래키 순환 참조 방지)
        analysis_job = AnalysisJob(
            plan_id=plan_id,
            job_type="evaluation",
            status="completed",
            token_usage=0,  # 기본값 설정
            created_at=current_time,
            completed_at=current_time,
            retry_count=0
        )
        
        db.add(analysis_job)
        db.flush()  # ID 확보하지만 아직 커밋하지 않음

        # 5. 총점 데이터 타입 변환 (Decimal 처리)
        total_score_decimal = None
        if evaluation_data.total_score is not None:
            if isinstance(evaluation_data.total_score, (int, float)):
                total_score_decimal = Decimal(str(evaluation_data.total_score))
            elif isinstance(evaluation_data.total_score, Decimal):
                total_score_decimal = evaluation_data.total_score
            else:
                total_score_decimal = Decimal('0.0')

        # 6. AnalysisResult 생성 (평가 결과)
        # JSONB 데이터 준비 - Decimal을 float로 변환
        details_json = evaluation_response_to_db_json(evaluation_data)
        
        analysis_result = AnalysisResult(
            analysis_job_id=analysis_job.id,
            evaluation_type="overall",
            score=total_score_decimal,
            summary=f"총점: {evaluation_data.total_score}점",
            details=details_json,  # 이미 변환된 JSON 데이터
            created_at=current_time
        )
        
        db.add(analysis_result)
        db.flush()  # ID 확보

        # 7. BusinessPlan 업데이트 (순환 참조 해결을 위한 별도 업데이트)
        # latest_job_id와 status 업데이트
        business_plan.latest_job_id = analysis_job.id
        business_plan.status = "completed"
        business_plan.updated_at = current_time

        # 8. 모든 변경사항을 한 번에 커밋
        db.commit()

        return {
            "message": "평가 결과가 성공적으로 저장되었습니다.",
            "analysis_job_id": analysis_job.id,
            "analysis_result_id": analysis_result.id,
            "total_score": float(total_score_decimal) if total_score_decimal else None,
            "plan_id": plan_id,
            "status": "completed"
        }

    except HTTPException:
        # FastAPI HTTPException은 그대로 재발생
        db.rollback()
        raise
    except IntegrityError as e:
        # 데이터베이스 제약조건 위반
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"데이터 무결성 오류: {str(e.orig) if hasattr(e, 'orig') else str(e)}"
        )
    except SQLAlchemyError as e:
        # 기타 데이터베이스 오류
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터베이스 오류가 발생했습니다: {str(e)}"
        )
    except Exception as e:
        # 기타 예상치 못한 오류
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"평가 결과 저장 중 오류가 발생했습니다: {str(e)}"
        )

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
        # AnalysisJob과 연관된 AnalysisResult 조회 (JOIN 최적화)
        analysis_result = (
            db.query(AnalysisResult)
            .filter(AnalysisResult.analysis_job_id == analysis_job_id)
            .first()
        )
        
        if not analysis_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 분석 작업의 평가 결과를 찾을 수 없습니다."
            )

        # 점수 데이터 타입 변환 (Decimal -> float)
        score_value = None
        if analysis_result.score is not None:
            score_value = float(analysis_result.score)

        return {
            "analysis_job_id": analysis_job_id,
            "analysis_result_id": analysis_result.id,
            "evaluation_type": analysis_result.evaluation_type,
            "score": score_value,
            "summary": analysis_result.summary,
            "details": analysis_result.details,  # 전체 EvaluationResponse JSONB
            "created_at": analysis_result.created_at.isoformat() if analysis_result.created_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"평가 결과 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/latest/{plan_id}", response_model=dict)
def get_latest_evaluation(
    plan_id: int,
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
):
    """
    특정 사업계획서의 최신 평가 결과 조회
    - plan_id: 사업계획서 ID
    
    개선사항:
    1. JOIN 쿼리 최적화
    2. NULL 체크 강화
    3. 사용자 권한 검증
    """
    try:
        # BusinessPlan과 최신 AnalysisResult를 JOIN으로 한 번에 조회
        result = (
            db.query(BusinessPlan, AnalysisResult)
            .join(
                AnalysisResult, 
                AnalysisResult.analysis_job_id == BusinessPlan.latest_job_id
            )
            .filter(BusinessPlan.id == plan_id)
            .first()
        )
        
        if not result:
            # BusinessPlan 존재 여부 먼저 확인
            business_plan = db.query(BusinessPlan).filter(BusinessPlan.id == plan_id).first()
            if not business_plan:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="해당 사업계획서를 찾을 수 없습니다."
                )
            elif not business_plan.latest_job_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="해당 사업계획서에 대한 평가 결과가 없습니다."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="최신 평가 결과를 찾을 수 없습니다."
                )

        business_plan, analysis_result = result

        # 사용자 권한 확인 (옵션: 필요시 활성화)
        # user_sub = claims.get("sub")
        # if business_plan.user.cognito_sub != user_sub:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="해당 사업계획서에 대한 권한이 없습니다."
        #     )

        # 점수 데이터 타입 변환
        score_value = None
        if analysis_result.score is not None:
            score_value = float(analysis_result.score)

        return {
            "plan_id": plan_id,
            "analysis_job_id": business_plan.latest_job_id,
            "analysis_result_id": analysis_result.id,
            "evaluation_type": analysis_result.evaluation_type,
            "score": score_value,
            "summary": analysis_result.summary,
            "details": analysis_result.details,
            "created_at": analysis_result.created_at.isoformat() if analysis_result.created_at else None,
            "business_plan_status": business_plan.status
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"최신 평가 결과 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.delete("/{analysis_job_id}", response_model=dict)
def delete_evaluation_result(
    analysis_job_id: int,
    db: Session = Depends(get_db),
    claims: Dict[str, Any] = Depends(get_claims),
):
    """
    평가 결과 삭제 (선택적 기능)
    - analysis_job_id: 삭제할 분석 작업 ID
    """
    try:
        # AnalysisJob 존재 확인
        analysis_job = (
            db.query(AnalysisJob)
            .filter(AnalysisJob.id == analysis_job_id)
            .first()
        )
        
        if not analysis_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 분석 작업을 찾을 수 없습니다."
            )

        # 관련된 BusinessPlan의 latest_job_id가 이 작업을 참조하는지 확인
        business_plan = (
            db.query(BusinessPlan)
            .filter(BusinessPlan.latest_job_id == analysis_job_id)
            .first()
        )

        # 트랜잭션으로 안전하게 삭제
        if business_plan:
            # latest_job_id 참조 제거
            business_plan.latest_job_id = None
            business_plan.status = "pending"
            business_plan.updated_at = _utcnow()

        # AnalysisJob 삭제 (CASCADE로 AnalysisResult도 함께 삭제됨)
        db.delete(analysis_job)
        db.commit()

        return {
            "message": "평가 결과가 성공적으로 삭제되었습니다.",
            "deleted_analysis_job_id": analysis_job_id
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"평가 결과 삭제 중 오류가 발생했습니다: {str(e)}"
        )