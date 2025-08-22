from botocore.exceptions import ClientError, BotoCoreError
from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

def to_http_exception(err: Exception) -> HTTPException:
    """
    Boto3 클라이언트 예외를 FastAPI의 HTTPException으로 변환합니다.
    """
    if isinstance(err, ClientError):
        # ClientError에서 HTTP 상태 코드와 메시지를 추출
        error_code = err.response.get("Error", {}).get("Code", "UnknownError")
        message = err.response.get("Error", {}).get("Message", str(err))
        status_code = err.response.get("ResponseMetadata", {}).get("HTTPStatusCode", HTTP_500_INTERNAL_SERVER_ERROR)

        # S3에서 발생하는 일반적인 오류 코드를 HTTP 상태 코드와 연결
        if error_code in ["NoSuchBucket", "NoSuchKey"]:
            status_code = HTTP_400_BAD_REQUEST

        return HTTPException(
            status_code=status_code,
            detail=f"S3 Client Error: {message} ({error_code})",
        )
    
    # BotoCoreError (네트워크 연결 등) 또는 기타 예외
    elif isinstance(err, BotoCoreError):
        return HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"S3 Connection Error: {str(err)}",
        )
    
    # 그 외 일반적인 예외
    else:
        return HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(err)}",
        )