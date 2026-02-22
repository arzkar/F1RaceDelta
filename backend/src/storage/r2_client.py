import boto3
from botocore.exceptions import ClientError
import logging
from typing import Optional

from src.core.config import settings

logger = logging.getLogger(__name__)

class R2Client:
    def __init__(self):
        # We explicitly configure the endpoint_url for Cloudflare R2
        self.s3_client = boto3.client(
            service_name="s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto", # R2 uses 'auto' region inherently
        )
        self.bucket = settings.R2_BUCKET_NAME

    def upload_file(self, file_path: str, object_name: str) -> bool:
        """
        Upload a file to the R2 bucket.
        """
        try:
            self.s3_client.upload_file(file_path, self.bucket, object_name)
            logger.info(f"Successfully uploaded {file_path} to {self.bucket}/{object_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload {file_path} to R2: {e}")
            return False

    def generate_presigned_url(self, object_name: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL to share an R2 object securely (e.g., streaming .parquet).
        """
        try:
            response = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": object_name},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {object_name}: {e}")
            return None

    def read_file_stream(self, object_name: str):
        """
        Get the raw object stream for pandas/polars to read directly without touching disk.
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=object_name)
            return response["Body"]
        except ClientError as e:
            logger.error(f"Failed to stream {object_name} from R2: {e}")
            return None

# Singleton-esque instantiaton for dependency injection later
r2_client = R2Client()
