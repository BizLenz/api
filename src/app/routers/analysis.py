from fastapi import APIRouter, Depends, HTTPException, Body
from app.schemas.evaluation import EvaluationRequest, EvaluationResponse, RequestindustryData, ResponseindustryData
import httpx 
import json
from pathlib import Path
from google.generativeai as genai

#google API 키 설정
from app.core.config import API_KEY
genai.configure(api_key=API_KEY)
import requests

# API 인스턴스 생성(analysis로 URL 그룹화 및 Swagger UI 분류)
router = APIRouter(prefix="/analysis",tag=["analysis"]) 

# 프롬프트 로드 함수 (프롬프트 텍스트들은 json화 필요)
def load_prompts():
    try:
        prompt_file = Path(__file__).schemas/"prompts.json"
        with open(prompt_file,'r',encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
             "default": "재시도 요청 바람"
        }

def analyze_with_gemini(prompt_text:str, business_plan_content:str)->str:
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        sections_text = ""
        total_max_score = 0
        
        for section in sections:
            sections_text +=f"\n섹션명: {section['section_name']}(최대 점수:{section['max_score']}점\n)"
            sections_text += "평가 질문들:\n"
            for question in section['questions']:
                sections_text +=f"- {question}\n"
            sections_text += "\n"
            total_max_score +=section['max_score']

        # 전체 프롬프트 생성 내용(Gemini에게 전달할 것)
        full_prompt = f"""
{prompt_text}

사업계획서 내용:
{business_plan_content}
평가섹션들:
{sections_text}
위 사업계획서를 다음 섹션들을 기준으로 분석하여 아래 형식으로 답변해주세요:

1. 섹션별 점수 및 총점 (총 {total_max_score}점 만점)
   - 각 섹션별 점수와 근거를 명시해주세요

2. 각 섹션별 주요 강점
   - 섹션명을 명시하고 구체적인 강점을 설명해주세요

3. 각 섹션별 개선이 필요한 부분
   - 섹션명을 명시하고 구체적인 개선점을 제시해주세요

4. 구체적인 제안사항
   - 실행 가능한 구체적인 개선 방안을 제시해주세요

5. 종합 평가
   - 전체적인 사업계획서의 완성도와 실현 가능성을 평가해주세요
"""

        # gemini API 호출
        response = model.generate_content(full_prompt)
        
        if response and response.text:
            return response.text
        else:
            return "분석 결과를 생성할 수 없습니다."
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류가 발생했습니다: {str(e)}")
        

gateway_url="게이트웨이 url"

@router.post("/evaluate", reponse_model=EvaluationResponse)
async def request_evaluation(request: EvaluationRequest):
    if not request.business_plan:
        raise HTTPException(status_code=400, detail="사업계획서 내용이 필요합니다.")
    
    #기본 프롬프트 기반 평가
    base_prompt = "이 사업계획서를 종합적으로 평가해주세요"

    #sections를 dict 형태로 변환
    sections_dict = [section.dict() for section in request.sections]

    #Gemini로 분석 수행
    analysis_result = analyze_with_gemini(
        prompt_text=base_prompt,
        business_plan_content=request.business_plan,
        sections = sections_dict
    )
    return EvaluationResponse(
        result = analysis_result,
        sections_evaluated = [s.section_name for s in request.sections],
        total_max_score = sum(s.max_score for s in request.sections),
        evaluation_type = request.evaluation_type
    )


@router.post("/industry-data")
async def get_industry_data(data: RequestindustryData = Body(...)):

    payload={
        "keyword":data.keyword,
        "market_data": data.market_data.dict()
        "additional_data": data.additional_data
    }

    try :
        response = requests.post(gateway_url, json=data.dict(),timeout=10)
        response.raise_for_status()
        result = response.json()

        return ResponseindustryData(
            marketStatus=result.get('marketStatus','No data')
            expertOpinion= result.get('expertOpinion','No opinion')
            processed_data={
                "original_market_data": data.market_data.dict()
            }
        ) 
    except requests.exceptions.RequestException as e:
        return Reponse(
            marketStatus="Error fetching data"
            expertOpinion=f"Failed to call API Gateway: {str(e)}"
            processed_data=None
        )


    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API Gateway 호출 실패: {str(e)}")
