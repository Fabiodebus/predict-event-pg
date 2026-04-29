import boto3

from app.config import settings


def _client():
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
