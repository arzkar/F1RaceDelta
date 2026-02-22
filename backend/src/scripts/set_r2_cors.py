import logging
from src.core.config import settings
from src.storage.r2_client import r2_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_cors():
    cors_configuration = {
        'CORSRules': [{
            'AllowedHeaders': ['*'],
            'AllowedMethods': ['GET', 'HEAD'],
            'AllowedOrigins': ['*'], # In production restrict to your actual Vercel/Railway domain
            'ExposeHeaders': ['ETag', 'x-amz-request-id'],
            'MaxAgeSeconds': 3000
        }]
    }

    try:
        r2_client.s3_client.put_bucket_cors(
            Bucket=r2_client.bucket,
            CORSConfiguration=cors_configuration
        )
        logger.info(f"Successfully applied permissive CORS configuration to '{r2_client.bucket}' R2 bucket.")
    except Exception as e:
        logger.error(f"Failed to update CORS: {e}")

if __name__ == "__main__":
    update_cors()
