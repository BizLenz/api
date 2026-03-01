"""
S3-compatible storage service

Configure STORAGE_ENDPOINT_URL to point at a custom endpoint; leave it unset for AWS S3
"""

import hashlib
import json
import asyncio
from datetime import datetime
from typing import Dict, Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class S3Manager:
    """S3-compatible storage manager for analysis results"""

    def __init__(self):
        self.bucket_name = settings.storage_bucket_name
        self.region = settings.storage_region

        config = Config(
            max_pool_connections=50,
            retries={"max_attempts": 3},
        )

        client_kwargs: Dict[str, Any] = {
            "aws_access_key_id": settings.aws_access_key_id,
            "aws_secret_access_key": settings.aws_secret_access_key,
            "config": config,
        }
        if self.region:
            client_kwargs["region_name"] = self.region
        if settings.storage_endpoint_url:
            client_kwargs["endpoint_url"] = settings.storage_endpoint_url

        self.s3_client = boto3.client("s3", **client_kwargs)
        self.s3_resource = boto3.resource("s3", **client_kwargs)

    def _generate_s3_key(
        self, user_id: str, plan_id: int, analysis_id: int, file_type: str
    ) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"users/{user_id}/plans/{plan_id}/analyses/{analysis_id}/{file_type}_{timestamp}.json"

    def _calculate_checksum(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    async def upload_analysis_result(
        self,
        user_id: str,
        plan_id: int,
        analysis_id: int,
        analysis_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Upload analysis result JSON to S3-compatible storage"""
        json_content = json.dumps(analysis_data, ensure_ascii=False, indent=2)
        content_bytes = json_content.encode("utf-8")
        s3_key = self._generate_s3_key(user_id, plan_id, analysis_id, "analysis")

        metadata = {
            "user-id": str(user_id),
            "plan-id": str(plan_id),
            "analysis-id": str(analysis_id),
            "upload-time": datetime.now().isoformat(),
        }

        try:
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content_bytes,
                ContentType="application/json",
                Metadata=metadata,
                ServerSideEncryption="AES256",
            )
        except ClientError as e:
            code = e.response["Error"]["Code"]
            raise Exception(
                f"Storage upload failed [{code}]: {e.response['Error']['Message']}"
            )

        return {
            "storage_bucket": self.bucket_name,
            "storage_key": s3_key,
            "storage_region": self.region,
            "file_size": len(content_bytes),
            "file_checksum": self._calculate_checksum(content_bytes),
            "content_type": "application/json",
            "upload_status": "completed",
            "upload_completed_at": datetime.now(),
        }

    async def download_analysis_result(self, s3_key: str) -> Dict[str, Any]:
        """Download and parse a JSON analysis result from storage"""
        try:
            response = await asyncio.to_thread(
                self.s3_client.get_object, Bucket=self.bucket_name, Key=s3_key
            )
            content = response["Body"].read()
            return {
                "data": json.loads(content.decode("utf-8")),
                "last_modified": response["LastModified"],
                "content_length": response["ContentLength"],
                "etag": response["ETag"].strip('"'),
            }
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise Exception(f"Object not found: {s3_key}")
            raise Exception(
                f"Storage download failed: {e.response['Error']['Message']}"
            )

    def generate_presigned_url(
        self, s3_key: str, operation: str = "get_object", expiration: int = 3600
    ) -> str:
        """Generate a pre-signed URL for temporary object access"""
        try:
            return self.s3_client.generate_presigned_url(
                operation,
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            raise Exception(
                f"Pre-signed URL generation failed: {e.response['Error']['Message']}"
            )

    async def delete_files(self, s3_keys: list) -> Dict[str, Any]:
        """Batch-delete objects from storage"""
        if not s3_keys:
            return {"deleted": [], "errors": []}

        delete_objects = [{"Key": key} for key in s3_keys if key]
        if not delete_objects:
            return {"deleted": [], "errors": []}

        try:
            response = await asyncio.to_thread(
                self.s3_client.delete_objects,
                Bucket=self.bucket_name,
                Delete={"Objects": delete_objects},
            )
            deleted = [obj["Key"] for obj in response.get("Deleted", [])]
            errors = [
                {"key": obj["Key"], "error": obj["Message"]}
                for obj in response.get("Errors", [])
            ]
            return {"deleted": deleted, "errors": errors}
        except ClientError as e:
            raise Exception(
                f"Storage deletion failed: {e.response['Error']['Message']}"
            )


def get_s3_manager() -> S3Manager:
    """Factory: create an S3Manager instance"""
    return S3Manager()
