import os
import boto3
from pathlib import Path
from dotenv import load_dotenv

def upload_pdfs_to_s3(bucket_name, region, local_dir, s3_prefix):
    s3_client = boto3.client('s3', region_name=region)
    local_path = Path(local_dir)
    
    if not local_path.exists():
        print(f"Local directory {local_dir} not found.")
        return

    files = [f for f in local_path.glob('*.pdf')]
    print(f"Found {len(files)} PDFs in {local_dir}. Starting upload to s3://{bucket_name}/{s3_prefix}...")

    for file_path in files:
        s3_key = os.path.join(s3_prefix, file_path.name).replace("\\", "/")
        try:
            print(f"Uploading {file_path.name}...")
            s3_client.upload_file(str(file_path), bucket_name, s3_key)
        except Exception as e:
            print(f"Failed to upload {file_path.name}: {e}")

if __name__ == "__main__":
    load_dotenv() # Load variables from .env
    BUCKET = "aether-bucket-682871415289-ap-south-2-an"
    REGION = "ap-south-2"
    LOCAL_DIR = "data/raw_pdfs"
    S3_PREFIX = "data/pdfs/"
    
    upload_pdfs_to_s3(BUCKET, REGION, LOCAL_DIR, S3_PREFIX)
    print("Upload complete.")
