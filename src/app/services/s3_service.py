"""
S3 연동 서비스 클래스
Gemini 분석 결과를 AWS S3에 안전하게 저장하고 관리하는 서비스
"""

import os
import hashlib
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config


class S3Manager:
    """S3 파일 관리 서비스"""
    
    def __init__(self):
        """S3 클라이언트 초기화"""
        self.region = os.getenv('AWS_REGION', 'ap-northeast-2')
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'bizlenz-analysis-results')
        
        # S3 클라이언트 설정 (성능 최적화)
        config = Config(
            region_name=self.region,
            max_pool_connections=50,
            retries={'max_attempts': 3}
        )
        
        try:
            self.s3_client = boto3.client('s3', config=config)
            self.s3_resource = boto3.resource('s3', config=config)
        except NoCredentialsError:
            raise Exception("AWS 자격 증명이 설정되지 않았습니다. AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY를 확인하세요.")
    
    def _generate_s3_key(self, user_id: int, plan_id: int, analysis_id: int, file_type: str) -> str:
        """S3 객체 키 생성"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"users/{user_id}/plans/{plan_id}/analyses/{analysis_id}/{file_type}_{timestamp}.json"
    
    def _calculate_checksum(self, content: bytes) -> str:
        """파일 체크섬 계산 (SHA256)"""
        return hashlib.sha256(content).hexdigest()
    
    async def upload_analysis_result(
        self,
        user_id: int,
        plan_id: int, 
        analysis_id: int,
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        분석 결과를 S3에 업로드
        
        Args:
            user_id: 사용자 ID
            plan_id: 사업계획서 ID
            analysis_id: 분석 ID
            analysis_data: 분석 결과 데이터
            
        Returns:
            업로드 결과 정보
        """
        try:
            # JSON 데이터를 바이트로 변환
            json_content = json.dumps(analysis_data, ensure_ascii=False, indent=2)
            content_bytes = json_content.encode('utf-8')
            
            # S3 키 생성
            s3_key = self._generate_s3_key(user_id, plan_id, analysis_id, "gemini_analysis")
            
            # 파일 메타데이터
            metadata = {
                'user-id': str(user_id),
                'plan-id': str(plan_id),
                'analysis-id': str(analysis_id),
                'upload-time': datetime.now().isoformat(),
                'file-type': 'gemini-analysis-result'
            }
            
            # S3 업로드
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content_bytes,
                ContentType='application/json',
                Metadata=metadata,
                ServerSideEncryption='AES256'
            )
            
            return {
                's3_bucket': self.bucket_name,
                's3_key': s3_key,
                's3_region': self.region,
                'file_size': len(content_bytes),
                'file_checksum': self._calculate_checksum(content_bytes),
                'content_type': 'application/json',
                'upload_status': 'completed',
                'upload_completed_at': datetime.now()
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = f"S3 업로드 실패 [{error_code}]: {e.response['Error']['Message']}"
            raise Exception(error_message)
        except Exception as e:
            raise Exception(f"분석 결과 업로드 중 오류 발생: {str(e)}")
    
    async def download_analysis_result(self, s3_key: str) -> Dict[str, Any]:
        """
        S3에서 분석 결과 다운로드
        
        Args:
            s3_key: S3 객체 키
            
        Returns:
            분석 결과 데이터
        """
        try:
            response = await asyncio.to_thread(
                self.s3_client.get_object,
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            content = response['Body'].read()
            analysis_data = json.loads(content.decode('utf-8'))
            
            return {
                'data': analysis_data,
                'last_modified': response['LastModified'],
                'content_length': response['ContentLength'],
                'etag': response['ETag'].strip('"')
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise Exception(f"파일을 찾을 수 없습니다: {s3_key}")
            else:
                raise Exception(f"S3 다운로드 실패: {e.response['Error']['Message']}")
        except json.JSONDecodeError:
            raise Exception("파일 형식이 올바르지 않습니다.")
        except Exception as e:
            raise Exception(f"분석 결과 다운로드 중 오류 발생: {str(e)}")
    
    def generate_presigned_url(
        self, 
        s3_key: str, 
        operation: str = 'get_object',
        expiration: int = 3600
    ) -> str:
        """
        프리사인드 URL 생성
        
        Args:
            s3_key: S3 객체 키
            operation: 작업 유형 ('get_object', 'put_object')
            expiration: 만료 시간 (초)
            
        Returns:
            프리사인드 URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                operation,
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
            
        except ClientError as e:
            raise Exception(f"프리사인드 URL 생성 실패: {e.response['Error']['Message']}")
    
    async def delete_analysis_files(self, s3_keys: list) -> Dict[str, Any]:
        """
        분석 관련 파일들을 S3에서 삭제
        
        Args:
            s3_keys: 삭제할 S3 키 리스트
            
        Returns:
            삭제 결과
        """
        if not s3_keys:
            return {'deleted': [], 'errors': []}
        
        try:
            # 배치 삭제를 위한 객체 리스트 생성
            delete_objects = [{'Key': key} for key in s3_keys if key]
            
            if not delete_objects:
                return {'deleted': [], 'errors': []}
            
            response = await asyncio.to_thread(
                self.s3_client.delete_objects,
                Bucket=self.bucket_name,
                Delete={'Objects': delete_objects}
            )
            
            deleted = [obj['Key'] for obj in response.get('Deleted', [])]
            errors = [
                {'key': obj['Key'], 'error': obj['Message']} 
                for obj in response.get('Errors', [])
            ]
            
            return {
                'deleted': deleted,
                'errors': errors,
                'total_deleted': len(deleted),
                'total_errors': len(errors)
            }
            
        except ClientError as e:
            raise Exception(f"S3 파일 삭제 실패: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"파일 삭제 중 오류 발생: {str(e)}")
    
    async def archive_analysis(self, s3_key: str) -> str:
        """
        분석 결과를 아카이브 스토리지로 이동
        
        Args:
            s3_key: 원본 S3 키
            
        Returns:
            아카이브된 S3 키
        """
        try:
            # 아카이브 키 생성 (archive/ 접두사 추가)
            archive_key = f"archive/{s3_key}"
            
            # 객체 복사 (GLACIER 스토리지 클래스로)
            await asyncio.to_thread(
                self.s3_client.copy_object,
                Bucket=self.bucket_name,
                CopySource={'Bucket': self.bucket_name, 'Key': s3_key},
                Key=archive_key,
                StorageClass='GLACIER',
                MetadataDirective='COPY'
            )
            
            return archive_key
            
        except ClientError as e:
            raise Exception(f"아카이브 실패: {e.response['Error']['Message']}")
    
    def get_bucket_info(self) -> Dict[str, Any]:
        """버킷 정보 조회"""
        try:
            # 버킷 존재 확인
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            
            # 버킷 위치 조회
            location = self.s3_client.get_bucket_location(Bucket=self.bucket_name)
            
            return {
                'bucket_name': self.bucket_name,
                'region': location.get('LocationConstraint', 'us-east-1'),
                'exists': True
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return {
                    'bucket_name': self.bucket_name,
                    'exists': False,
                    'error': 'Bucket does not exist'
                }
            else:
                raise Exception(f"버킷 정보 조회 실패: {e.response['Error']['Message']}")


# 싱글톤 인스턴스
s3_manager = S3Manager()