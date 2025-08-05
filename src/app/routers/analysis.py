from fastapi imprt APIRouter, Depends
from app.schemas.evaluation import EvaluationRequest, EvaluationResponse
import httpx 
import json
from pathlib import Path

PROMPT_FILE = Path("파일 경로 적기".p) # 파일 경로로 바꿀것

# API 인스턴스 생성(analysis로 URL 그룹화 및 Swagger UI 분류)
router = APIRouter(prefix="/analysis",tag=["analysis"]) 

# 프롬프트 로드 함수 (프롬프트 텍스트들은 json화 필요)
def load_prompts():
    with open(PROMPT_FILE, "r") as f:
        return json.load(f)


@router.post("/evaluate", reponse_model=EvaluationRequest)
async def request_evaluation(request: EvaluationReques=Depends()):
    prompts = load_prompts()
    """
    관련 로직 처리
    1. UI를 통한 프롬프트 텍스트 생성
    2. 프롬프트 Gemini한테 먹이기
    3. Gemini 분석 결과 가져오기
    """
    # 클라이언트 데이터 결합
    full_prompt = ㄹ"{base_prompt}\n기준:{request.evaluation_criteria}\n추가정보:{request.additional_info}"

    gateway_url="게이트웨이 url"
    async with httpx.AsyncClient() as client:
        response = await client.post(gateway_url,json=:"prompt":full_prompt)
        if response.status_code != 200:
            return EvaluationResponse(error="분석 서버 오류",result = "")

    analysis=response.json().get("result")

    return EvaluationResponse(
        result = analysis,
        score=8-,
        suggestions=["개선점1","개선점 2"]
    )