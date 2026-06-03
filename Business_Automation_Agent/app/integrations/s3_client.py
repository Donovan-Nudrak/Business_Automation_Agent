import uuid
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class S3Client:
    def __init__(
        self,
        *,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        region: str | None = None,
        bucket: str | None = None,
    ) -> None:
        self.region = region or settings.AWS_REGION
        self.bucket = bucket or settings.AWS_S3_BUCKET
        self._client = boto3.client(
            "s3",
            aws_access_key_id=access_key_id or settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=(
                secret_access_key or settings.AWS_SECRET_ACCESS_KEY or None
            ),
            region_name=self.region,
        )

    def generate_object_key(
        self,
        event_id: uuid.UUID,
        report_type: str = "json",
    ) -> str:
        from app.documents.report_generator import generate_object_key

        return generate_object_key(event_id, report_type)

    def upload_pdf(self, data: bytes, key: str) -> str:
        return self.upload_bytes(data, key, content_type="application/pdf")

    def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str = "application/json",
    ) -> str:
        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return self.build_object_url(key)

    def upload_file(
        self,
        file_path: str,
        key: str,
        content_type: str = "application/json",
    ) -> str:
        path = Path(file_path)
        self._client.upload_file(
            str(path),
            self.bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return self.build_object_url(key)

    def object_exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def build_object_url(self, key: str) -> str:
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"

    def extract_key_from_url(self, s3_url: str) -> str | None:
        if not s3_url:
            return None

        virtual_host_prefix = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/"
        if s3_url.startswith(virtual_host_prefix):
            return s3_url[len(virtual_host_prefix) :]

        legacy_prefix = f"https://s3.{self.region}.amazonaws.com/{self.bucket}/"
        if s3_url.startswith(legacy_prefix):
            return s3_url[len(legacy_prefix) :]

        return None

    def generate_presigned_url(
        self,
        key: str,
        expire_seconds: int | None = None,
    ) -> str:
        expires_in = expire_seconds or settings.PRESIGNED_URL_EXPIRE_SECONDS
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )


def get_s3_client() -> S3Client:
    return S3Client()
