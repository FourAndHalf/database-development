#!/usr/bin/env python3
import os
import json
import logging
from pathlib import Path
import argparse
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Ensure we can import services
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from docling.document_converter import DocumentConverter
from services.ingestion.pdf_parser import PdfParser
from services.ingestion.vectorize import Vectorizer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_pdfs_from_s3(bucket_name, prefix, local_dir):
    """
    Downloads all PDFs under the specified prefix in the S3 bucket to a local directory.
    """
    s3_client = boto3.client('s3')
    local_path = Path(local_dir)
    local_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Listing files in S3 bucket '{bucket_name}' under prefix '{prefix}'...")
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        
        pdf_keys = []
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.lower().endswith('.pdf'):
                        pdf_keys.append(key)
                        
        if not pdf_keys:
            logger.warning(f"No PDF files found in s3://{bucket_name}/{prefix}")
            return []
            
        logger.info(f"Found {len(pdf_keys)} PDF files. Downloading...")
        downloaded_paths = []
        
        for key in pdf_keys:
            filename = Path(key).name
            dest_path = local_path / filename
            
            # Simple skip if already exists locally
            if dest_path.exists():
                logger.info(f"File {filename} already exists locally. Skipping download.")
                downloaded_paths.append(dest_path)
                continue
                
            try:
                logger.info(f"Downloading s3://{bucket_name}/{key} to {dest_path}...")
                s3_client.download_file(bucket_name, key, str(dest_path))
                downloaded_paths.append(dest_path)
            except ClientError as e:
                logger.error(f"Failed to download {key}: {e}")
                
        return downloaded_paths
    except Exception as e:
        logger.error(f"Error listing S3 bucket: {e}")
        return []

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Ingest PDFs from AWS S3, parse, and vectorize them.")
    parser.add_argument("--bucket", type=str, default=os.getenv("AWS_S3_BUCKET_NAME"), help="AWS S3 bucket name")
    parser.add_argument("--prefix", type=str, default="pdfs/", help="S3 prefix (folder) containing the PDFs (e.g., pdfs/)")
    parser.add_argument("--local-dir", type=str, default="data/raw_pdfs", help="Local directory to download PDFs into")
    parser.add_argument("--parsed-dir", type=str, default="data/parsed", help="Local directory to store parsed structured JSONs")
    
    args = parser.parse_args()
    
    bucket = args.bucket
    prefix = args.prefix
    local_dir = args.local_dir
    parsed_dir = args.parsed_dir
    
    if not bucket:
        logger.error("AWS S3 bucket name is not set. Please provide it via --bucket or set AWS_S3_BUCKET_NAME in your environment/.env file.")
        return
        
    # Ensure prefix ends with a slash if it's not empty
    if prefix and not prefix.endswith('/'):
        prefix += '/'
        
    logger.info("=== STEP 1: Downloading PDFs from S3 ===")
    downloaded_files = download_pdfs_from_s3(bucket, prefix, local_dir)
    
    if not downloaded_files:
        logger.warning("No PDF files downloaded. Exiting pipeline.")
        return
        
    logger.info("=== STEP 2: Parsing PDFs to Structured JSON using Docling ===")
    converter = DocumentConverter()
    parser_instance = PdfParser(converter=converter, output_dir=Path(parsed_dir))
    
    for pdf_path in downloaded_files:
        logger.info(f"Parsing {pdf_path.name}...")
        parser_instance.parse_pdf(pdf_path)
        
    logger.info("=== STEP 3: Chunking, Embedding, and Storing in Vector DB ===")
    vectorizer = Vectorizer()
    vectorizer.vectorize_and_store()
    
    logger.info("Ingestion pipeline successfully completed!")

if __name__ == "__main__":
    main()
