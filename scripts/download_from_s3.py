#!/usr/bin/env python3
"""Re-download all documents from the S3 bucket into data/raw_pdfs.

Standalone download step (no parsing/embedding) for starting the pipeline fresh.

Usage:
    python scripts/download_from_s3.py                 # bucket + prefix from .env
    python scripts/download_from_s3.py --prefix pdfs/  # override prefix
    python scripts/download_from_s3.py --force         # re-download even if present
"""
import os
import sys
import argparse
import logging
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def download_all(bucket: str, prefix: str, dest_dir: Path, force: bool) -> int:
    s3 = boto3.client("s3")
    dest_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Listing s3://{bucket}/{prefix} ...")
    paginator = s3.get_paginator("list_objects_v2")

    downloaded = skipped = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):  # skip "folder" placeholder keys
                continue

            dest = dest_dir / Path(key).name
            if dest.exists() and not force:
                logger.info(f"Skipping (exists): {dest.name}")
                skipped += 1
                continue

            try:
                logger.info(f"Downloading {key} -> {dest}")
                s3.download_file(bucket, key, str(dest))
                downloaded += 1
            except ClientError as e:
                logger.error(f"Failed to download {key}: {e}")

    logger.info(f"Done. Downloaded {downloaded}, skipped {skipped}, total in {dest_dir}: "
                f"{len(list(dest_dir.glob('*')))} files.")
    return downloaded


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Re-download all documents from S3 into data/raw_pdfs.")
    parser.add_argument("--bucket", default=os.getenv("AWS_S3_BUCKET_NAME"), help="S3 bucket name")
    parser.add_argument("--prefix", default=os.getenv("S3_RAW_PDFS_PREFIX", "pdfs/"), help="S3 key prefix")
    parser.add_argument("--dest", default="data/raw_pdfs", help="Local destination directory")
    parser.add_argument("--force", action="store_true", help="Re-download files even if they already exist locally")
    args = parser.parse_args()

    if not args.bucket:
        logger.error("No bucket set. Pass --bucket or set AWS_S3_BUCKET_NAME in .env")
        return 1

    prefix = args.prefix
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    try:
        download_all(args.bucket, prefix, Path(args.dest), args.force)
    except NoCredentialsError:
        logger.error("AWS credentials not found. Set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY "
                     "in .env or use an EC2 instance role.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
