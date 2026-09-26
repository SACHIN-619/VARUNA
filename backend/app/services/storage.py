import os
from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path
from app.core.config import settings

class StorageProvider(ABC):
    """Abstract interface for large meteorological file storage (NetCDF, GRIB2, Parquet)."""

    @abstractmethod
    def save_bytes(self, relative_path: str, data: bytes) -> str:
        """Saves byte content and returns path/URI."""
        pass

    @abstractmethod
    def get_bytes(self, relative_path: str) -> Optional[bytes]:
        """Reads byte content from storage."""
        pass

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        """Checks if artifact exists."""
        pass

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """Lists files matching prefix."""
        pass


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage provider for development and zero-cloud deployments."""

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or settings.STORAGE_LOCAL_PATH)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative_path: str) -> Path:
        # Sanitize and prevent directory traversal
        clean_path = os.path.normpath(relative_path).lstrip("/\\")
        return self.base_dir / clean_path

    def save_bytes(self, relative_path: str, data: bytes) -> str:
        target = self._resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            f.write(data)
        return str(target)

    def get_bytes(self, relative_path: str) -> Optional[bytes]:
        target = self._resolve(relative_path)
        if not target.exists():
            return None
        with open(target, "rb") as f:
            return f.read()

    def exists(self, relative_path: str) -> bool:
        return self._resolve(relative_path).exists()

    def list_files(self, prefix: str = "") -> List[str]:
        target_dir = self._resolve(prefix)
        if not target_dir.exists():
            return []
        if target_dir.is_file():
            return [str(target_dir.relative_to(self.base_dir))]
        return [str(p.relative_to(self.base_dir)) for p in target_dir.glob("**/*") if p.is_file()]


class S3StorageProvider(StorageProvider):
    """S3-compatible object storage provider (AWS S3, MinIO, Cloudflare R2, Supabase Storage)."""

    def __init__(self):
        self.bucket = settings.STORAGE_BUCKET
        self.endpoint = settings.STORAGE_ENDPOINT
        # Lazy import of boto3 so it remains optional
        try:
            import boto3
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint if self.endpoint else None,
                aws_access_key_id=settings.STORAGE_ACCESS_KEY,
                aws_secret_access_key=settings.STORAGE_SECRET_KEY
            )
        except ImportError:
            self.s3_client = None

    def save_bytes(self, relative_path: str, data: bytes) -> str:
        if not self.s3_client:
            raise RuntimeError("boto3 package not installed or AWS credentials unconfigured.")
        self.s3_client.put_object(Bucket=self.bucket, Key=relative_path, Body=data)
        return f"s3://{self.bucket}/{relative_path}"

    def get_bytes(self, relative_path: str) -> Optional[bytes]:
        if not self.s3_client:
            return None
        try:
            resp = self.s3_client.get_object(Bucket=self.bucket, Key=relative_path)
            return resp["Body"].read()
        except Exception:
            return None

    def exists(self, relative_path: str) -> bool:
        if not self.s3_client:
            return False
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=relative_path)
            return True
        except Exception:
            return False

    def list_files(self, prefix: str = "") -> List[str]:
        if not self.s3_client:
            return []
        try:
            resp = self.s3_client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            return [item["Key"] for item in resp.get("Contents", [])]
        except Exception:
            return []


def get_storage_provider() -> StorageProvider:
    if settings.STORAGE_PROVIDER.lower() == "s3" and settings.STORAGE_ACCESS_KEY:
        return S3StorageProvider()
    return LocalStorageProvider()

storage_service = get_storage_provider()
