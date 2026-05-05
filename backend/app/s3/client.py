from functools import lru_cache

import boto3

from app.config import settings


@lru_cache(maxsize=1)
def _client():
    """Cached module-level boto3 S3 client. Tests must call _client.cache_clear()
    when entering a fresh moto mock_aws() context, since the cached client's
    transport layer is bound to the patch active at construction time.
    """
    return boto3.client("s3", region_name=settings.aws_region)


def get_presigned_put_url(key: str, expires_in: int = 300) -> str:
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.aws_s3_bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def get_presigned_get_url(key: str, expires_in: int = 300) -> str:
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.aws_s3_bucket, "Key": key},
        ExpiresIn=expires_in,
    )
