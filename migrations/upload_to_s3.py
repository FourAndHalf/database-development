import os
import logging
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def upload_directory_to_s3(s3_client, bucket_name: str, local_dir: str, s3_prefix: str):
    """
    Recursively uploads all files from a local directory to an S3 bucket under a specific prefix.
    """
    local_path = Path(local_dir)
    if not local_path.exists() or not local_path.is_dir():
        logger.warning(f"Local directory '{local_dir}' does not exist. Skipping.")
        return

    files_to_upload = [f for f in local_path.glob('**/*') if f.is_file()]
    if not files_to_upload:
        logger.info(f"No files found in '{local_dir}'. Skipping.")
        return

    logger.info(f"Found {len(files_to_upload)} files in '{local_dir}' to upload to s3://{bucket_name}/{s3_prefix}")
    
    for file_path in files_to_upload:
        # Calculate relative path to maintain directory structure
        rel_path = file_path.relative_to(local_path)
        
        # Ensure forward slashes for S3 keys regardless of OS
        s3_key = os.path.join(s3_prefix, str(rel_path)).replace("\\", "/") 
        
        try:
            logger.info(f"Uploading {file_path.name} to s3://{bucket_name}/{s3_key}...")
            s3_client.upload_file(str(file_path), bucket_name, s3_key)
        except ClientError as e:
            logger.error(f"Failed to upload {file_path}: {e}")

def main():
    """
    Main execution script to migrate local artifacts to AWS S3.
    """
    load_dotenv()
    
    bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
    if not bucket_name:
        logger.error("AWS_S3_BUCKET_NAME environment variable is not set. Cannot proceed with migration.")
        return

    try:
        s3_client = boto3.client('s3')
        # Attempt to head the bucket to verify credentials and access
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        logger.error(f"Failed to access bucket '{bucket_name}'. Check your AWS credentials and permissions. Error: {e}")
        return
    except Exception as e:
        logger.error(f"Failed to initialize S3 client: {e}")
        return

    # Define mappings of local directories to their corresponding S3 prefixes
    migrations = [
        (
            os.getenv("LOCAL_RAW_PDFS_DIR", "data/raw_pdfs"),
            os.getenv("S3_RAW_PDFS_PREFIX", "raw_pdfs/")
        ),
        (
            os.getenv("LOCAL_PARSED_DIR", "data/parsed"),
            os.getenv("S3_PARSED_PREFIX", "parsed/")
        ),
        (
            os.getenv("LOCAL_CHUNKS_DIR", "data/chunks"),
            os.getenv("S3_CHUNKS_PREFIX", "chunks/")
        ),
        (
            os.getenv("LOCAL_EMBEDDINGS_DIR", "data/embeddings"),
            os.getenv("S3_EMBEDDINGS_PREFIX", "embeddings/")
        )
    ]

    logger.info(f"Starting data migration to S3 Bucket: '{bucket_name}'")
    
    for local_dir, s3_prefix in migrations:
        # Ensure s3_prefix ends with a slash if it's acting as a directory root
        if not s3_prefix.endswith('/'):
            s3_prefix += '/'
        
        upload_directory_to_s3(s3_client, bucket_name, local_dir, s3_prefix)

    logger.info("Migration script completed.")

if __name__ == "__main__":
    main()
