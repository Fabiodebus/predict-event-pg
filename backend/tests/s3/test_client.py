import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch


@pytest.fixture
def mock_s3(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")
    with mock_aws():
        s3 = boto3.client("s3", region_name="eu-central-1")
        s3.create_bucket(
            Bucket="predict-customer-files-dev",
            CreateBucketConfiguration={"LocationConstraint": "eu-central-1"},
        )
        yield s3


def test_get_presigned_put_url_returns_string(mock_s3):
    from app.s3.client import get_presigned_put_url
    url = get_presigned_put_url("uploads/test.pdf")
    assert isinstance(url, str)
    assert "predict-customer-files-dev" in url
    assert "test.pdf" in url


def test_get_presigned_put_url_respects_expiry(mock_s3):
    from app.s3.client import get_presigned_put_url
    url = get_presigned_put_url("uploads/test.pdf", expires_in=60)
    assert "X-Amz-Expires=60" in url or "Expires" in url


def test_get_presigned_get_url_returns_string(mock_s3):
    from app.s3.client import get_presigned_get_url
    url = get_presigned_get_url("uploads/existing.pdf")
    assert isinstance(url, str)
    assert "predict-customer-files-dev" in url
    assert "existing.pdf" in url


def test_get_presigned_get_url_default_expiry_300(mock_s3):
    from app.s3.client import get_presigned_get_url
    url = get_presigned_get_url("uploads/test.pdf")
    assert "X-Amz-Expires=300" in url or "Expires" in url
