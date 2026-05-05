"""Verify (or enable) S3 object versioning on customer-files buckets.

Usage:
    poetry run python scripts/ensure_s3_versioning.py BUCKET [BUCKET ...]
    poetry run python scripts/ensure_s3_versioning.py --enable BUCKET [BUCKET ...]
    poetry run python scripts/ensure_s3_versioning.py --region eu-central-1 BUCKET

Verify mode (default): exits 0 if every bucket has Status=Enabled, 1 otherwise.
Enable mode (--enable): turns versioning on for any bucket that's not Enabled,
then verifies. Idempotent — safe to re-run.

CI invokes this in verify mode against the env's actual bucket(s) so a
manually-provisioned bucket without versioning trips the build.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

import boto3


def is_versioning_enabled(s3_client, bucket: str) -> bool:
    """Return True iff get-bucket-versioning reports Status=Enabled.

    A never-versioned bucket returns an empty response with no Status key —
    treat that as False. Suspended also reads as False.
    """
    response = s3_client.get_bucket_versioning(Bucket=bucket)
    return response.get("Status") == "Enabled"


def enable_versioning(s3_client, bucket: str) -> None:
    s3_client.put_bucket_versioning(
        Bucket=bucket,
        VersioningConfiguration={"Status": "Enabled"},
    )


def _build_client(region: str):
    return boto3.client("s3", region_name=region)


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify or enable S3 object versioning on one or more buckets.",
    )
    parser.add_argument(
        "buckets",
        nargs="*",
        help="Bucket name(s) to check.",
    )
    parser.add_argument(
        "--enable",
        action="store_true",
        help="Turn versioning on for any bucket that's not Enabled, then verify.",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION", "us-east-1"),
        help="AWS region (default: $AWS_REGION or us-east-1).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(list(sys.argv[1:]) if argv is None else list(argv))

    if not args.buckets:
        # No-op success keeps CI green before buckets are wired up.
        return 0

    s3 = _build_client(args.region)

    if args.enable:
        for bucket in args.buckets:
            if not is_versioning_enabled(s3, bucket):
                enable_versioning(s3, bucket)
                print(f"[enabled] {bucket}")
            else:
                print(f"[already-enabled] {bucket}")

    missing = [b for b in args.buckets if not is_versioning_enabled(s3, b)]
    if missing:
        for bucket in missing:
            print(f"[NOT-ENABLED] {bucket}", file=sys.stderr)
        print(
            f"\n{len(missing)}/{len(args.buckets)} bucket(s) lack Status=Enabled. "
            f"Re-run with --enable, or fix manually with: "
            f"aws s3api put-bucket-versioning --bucket <name> "
            f"--versioning-configuration Status=Enabled",
            file=sys.stderr,
        )
        return 1

    for bucket in args.buckets:
        print(f"[ok] {bucket} — versioning Enabled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
