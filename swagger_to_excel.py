import pandas as pd
import requests
from datetime import datetime

def swagger_to_excel(swagger_url, output_file):
    """Swagger OpenAPI 스펙을 엑셀 파일로 변환"""
    
    try:
        # OpenAPI 스펙 가져오기
        print(f"Fetching OpenAPI spec from {swagger_url}...")
        response = requests.get(swagger_url)
        response.raise_for_status()
        spec = response.json()
        
        # API 정보 파싱
        apis = []
        
        for path, methods in spec.get('paths', {}).items():
            for method, details in methods.items():
                
                # 파라미터 정보 추출
                parameters = []
                if 'parameters' in details:
                    for param in details['parameters']:
                        param_info = f"{param.get('name', '')} ({param.get('in', '')}) - {param.get('description', '')}"
                        parameters.append(param_info)
                
                # Request Body 정보 추출
                request_body = ""
                if 'requestBody' in details:
                    content = details['requestBody'].get('content', {})
                    for content_type, schema_info in content.items():
                        request_body = f"{content_type}"
                        break
                
                # Response 정보 추출
                responses = []
                if 'responses' in details:
                    for code, resp_info in details['responses'].items():
                        desc = resp_info.get('description', '')
                        responses.append(f"{code}: {desc}")
                
                # Tags 정보
                tags = ', '.join(details.get('tags', []))
                
                apis.append({
                    'Path': path,
                    'Method': method.upper(),
                    'Summary': details.get('summary', ''),
                    'Description': details.get('description', ''),
                    'Tags': tags,
                    'Parameters': '; '.join(parameters) if parameters else '',
                    'Request Body': request_body,
                    'Responses': '; '.join(responses) if responses else '',
                    'Deprecated': details.get('deprecated', False)
                })
        
        # DataFrame 생성 및 엑셀 저장
        df = pd.DataFrame(apis)
        
        # 엑셀 writer 설정 (여러 시트 생성)
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            
            # 전체 API 목록
            df.to_excel(writer, sheet_name='All APIs', index=False)
            
            # Tags별 시트 생성
            for tag in df['Tags'].unique():
                if tag:  # 빈 태그 제외
                    tag_df = df[df['Tags'].str.contains(tag, na=False)]
                    safe_tag_name = tag.replace('/', '_')[:30]  # 시트명 길이 제한
                    tag_df.to_excel(writer, sheet_name=safe_tag_name, index=False)
            
            # 메타데이터 시트
            metadata = {
                'Info': ['API Title', 'Version', 'Description', 'Generated At'],
                'Value': [
                    spec.get('info', {}).get('title', 'N/A'),
                    spec.get('info', {}).get('version', 'N/A'), 
                    spec.get('info', {}).get('description', 'N/A'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ]
            }
            metadata_df = pd.DataFrame(metadata)
            metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
        
        print(f"Excel file created: {output_file}")
        print(f"Total APIs: {len(apis)}")
        print(f"Tags found: {', '.join(df['Tags'].unique())}")
        
    except requests.RequestException as e:
        print(f"Error fetching OpenAPI spec: {e}")
    except Exception as e:
        print(f"Error converting to Excel: {e}")

if __name__ == "__main__":
    # 설정
    SWAGGER_URL = "http://localhost:8000/openapi.json"
    OUTPUT_FILE = "bizlenz_api_documentation.xlsx"
    
    # 변환 실행
    swagger_to_excel(SWAGGER_URL, OUTPUT_FILE)
