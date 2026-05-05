"""Tests for scripts/ensure_s3_versioning.py.

The script exists so versioning on customer-files buckets is self-enforcing rather
than dependent on someone reading a runbook. CI invokes it in verify mode; ops
runs it once with --enable when provisioning a new bucket.
"""

import boto3
import pytest
from moto import mock_aws

from scripts.ensure_s3_versioning import (
    enable_versioning,
    is_versioning_enabled,
    main,
)


REGION = "eu-central-1"
BUCKET_A = "predict-customer-files-test-a"
BUCKET_B = "predict-customer-files-test-b"


@pytest.fixture
def s3():
    with mock_aws():
        client = boto3.client("s3", region_name=REGION)
        for bucket in (BUCKET_A, BUCKET_B):
            client.create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration={"LocationConstraint": REGION},
            )
        yield client


def test_is_versioning_enabled_false_on_fresh_bucket(s3):
    assert is_versioning_enabled(s3, BUCKET_A) is False


def test_enable_versioning_flips_status_to_enabled(s3):
    enable_versioning(s3, BUCKET_A)
    assert is_versioning_enabled(s3, BUCKET_A) is True


def test_is_versioning_enabled_false_when_suspended(s3):
    s3.put_bucket_versioning(
        Bucket=BUCKET_A, VersioningConfiguration={"Status": "Suspended"}
    )
    assert is_versioning_enabled(s3, BUCKET_A) is False


def test_main_verify_returns_0_when_all_enabled(s3, monkeypatch):
    enable_versioning(s3, BUCKET_A)
    enable_versioning(s3, BUCKET_B)
    monkeypatch.setattr(
        "scripts.ensure_s3_versioning._build_client", lambda region: s3
    )
    exit_code = main([BUCKET_A, BUCKET_B, "--region", REGION])
    assert exit_code == 0


def test_main_verify_returns_1_when_any_missing(s3, monkeypatch):
    enable_versioning(s3, BUCKET_A)
    # BUCKET_B left as fresh — versioning unset
    monkeypatch.setattr(
        "scripts.ensure_s3_versioning._build_client", lambda region: s3
    )
    exit_code = main([BUCKET_A, BUCKET_B, "--region", REGION])
    assert exit_code == 1


def test_main_enable_flag_flips_then_verifies(s3, monkeypatch):
    monkeypatch.setattr(
        "scripts.ensure_s3_versioning._build_client", lambda region: s3
    )
    exit_code = main([BUCKET_A, BUCKET_B, "--region", REGION, "--enable"])
    assert exit_code == 0
    assert is_versioning_enabled(s3, BUCKET_A) is True
    assert is_versioning_enabled(s3, BUCKET_B) is True


def test_main_returns_0_when_no_buckets_passed(s3, monkeypatch):
    """Empty bucket list is a no-op success — keeps CI green when not yet wired up."""
    monkeypatch.setattr(
        "scripts.ensure_s3_versioning._build_client", lambda region: s3
    )
    exit_code = main(["--region", REGION])
    assert exit_code == 0
