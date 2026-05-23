from __future__ import annotations

import argparse
import logging
import sys
import os
import tempfile
from pathlib import Path

from docling.document_converter import DocumentConverter
from docling.datamodel.document import DoclingDocument
from dotenv import load_dotenv

# Try importing boto3
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PdfParser:
    """
    Parses PDF documents into a structured format using the Docling library,
    preparing them for the subsequent chunking process.
    """

    def __init__(self, converter: DocumentConverter, output_dir: Path):
        """
        Initializes the PdfParser.

        Args:
            converter: An instance of the Docling DocumentConverter.
            output_dir: The directory to save the parsed JSON files.
        """
        self.converter = converter
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.s3_bucket = os.getenv("AWS_S3_BUCKET_NAME")
        self.s3_raw_prefix = os.getenv("S3_RAW_PDFS_PREFIX", "raw_pdfs/")
        if self.s3_bucket and BOTO3_AVAILABLE:
            self.s3_client = boto3.client('s3')
            logging.info(f"S3 integration enabled. Bucket: {self.s3_bucket}")
        else:
            self.s3_client = None
            if self.s3_bucket:
                logging.warning("S3 bucket set but boto3 is not available. Please install boto3.")

    def _download_from_s3(self, s3_key: str, local_path: Path) -> bool:
        """Downloads a file from S3 to a local path."""
        if not self.s3_client:
            return False
        try:
            logging.info(f"Downloading s3://{self.s3_bucket}/{s3_key} to {local_path}")
            self.s3_client.download_file(self.s3_bucket, s3_key, str(local_path))
            return True
        except ClientError as e:
            logging.error(f"Failed to download {s3_key} from S3: {e}")
            return False

    def parse_pdf(self, pdf_path: Path | str) -> DoclingDocument | None:
        """
        Parses a single PDF file using Docling. If S3 is configured and the path
        is just a filename, it attempts to fetch it from S3 first.

        Args:
            pdf_path: The path or filename to the PDF file to parse.

        Returns:
            A DoclingDocument object if parsing is successful, otherwise None.
        """
        # Convert string to Path
        if isinstance(pdf_path, str):
            pdf_path = Path(pdf_path)

        output_path = self.output_dir / f"{pdf_path.stem}.json"
        if output_path.exists():
            logging.info(f"Parsed file already exists, loading from cache: {output_path}")
            try:
                doc = DoclingDocument.load_from_json(output_path)
                return doc
            except Exception as e:
                logging.error(f"Failed to load cached JSON for {pdf_path}. Reparsing. Error: {e}")

        # Handle S3 fetching if the file doesn't exist locally but S3 is configured
        temp_file = None
        target_path = pdf_path
        
        if not target_path.exists() and self.s3_client:
            logging.info(f"File {pdf_path} not found locally. Attempting to fetch from S3.")
            s3_key = f"{self.s3_raw_prefix}{pdf_path.name}"
            # Create a temporary file to hold the S3 download
            fd, temp_path = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            temp_file = Path(temp_path)
            
            if self._download_from_s3(s3_key, temp_file):
                target_path = temp_file
            else:
                if temp_file.exists():
                    temp_file.unlink()
                return None

        if not target_path.exists():
            logging.warning(f"File not found: {target_path}")
            return None

        logging.info(f"Parsing PDF: {target_path}")
        try:
            # The core conversion step using the docling library
            result = self.converter.convert(target_path)
            doc = result.document
            
            # Save the parsed document as a JSON file using Docling's native method
            doc.save_as_json(output_path)
            logging.info(f"Successfully parsed and saved to {output_path}")
            
            return doc
        except Exception as e:
            logging.error(f"Failed to parse {target_path}. Error: {e}")
            return None
        finally:
            # Cleanup temporary S3 file if it was created
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError as e:
                    logging.warning(f"Failed to delete temp file {temp_file}: {e}")

def main():
    """
    Main tool entry point. Allows parsing a single file or a batch directory.
    """
    parser = argparse.ArgumentParser(
        description="Tool for parsing PDF documents into structured JSON using Docling."
    )
    
    # Allow either a single file OR an input directory, but not both
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--file",
        type=Path,
        help="Path to a single PDF file to parse.",
    )
    group.add_argument(
        "--input-dir",
        type=Path,
        help="Directory containing raw PDF files for batch processing.",
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(os.getenv("LOCAL_PARSED_DIR", "data/parsed")),
        help="Directory where the parsed JSON files will be saved (default: LOCAL_PARSED_DIR or data/parsed).",
    )
    
    args = parser.parse_args()
    
    load_dotenv()
    parsed_dir = args.output_dir.resolve()
    
    # Initialize the Docling converter. This object handles the complex
    # backend processing of turning a PDF into a structured DoclingDocument.
    converter = DocumentConverter()
    pdf_parser = PdfParser(converter=converter, output_dir=parsed_dir)
    
    if args.file:
        file_path = args.file.resolve()
        if not file_path.exists():
            logging.error(f"Input file not found: {file_path}")
            sys.exit(1)
        logging.info(f"Starting single-file parsing for '{file_path}'...")
        pdf_parser.parse_pdf(file_path)
        
    elif args.input_dir:
        raw_pdf_dir = args.input_dir.resolve()
        if not raw_pdf_dir.exists():
            logging.error(f"Input directory not found: {raw_pdf_dir}")
            sys.exit(1)
            
        logging.info(f"Starting batch PDF parsing process from '{raw_pdf_dir}'...")
        pdf_files = list(raw_pdf_dir.glob("*.pdf"))
        
        if not pdf_files:
            logging.warning(f"No PDF files found in {raw_pdf_dir}.")
            return

        for pdf_path in pdf_files:
            pdf_parser.parse_pdf(pdf_path)

    logging.info("PDF parsing process completed.")

if __name__ == "__main__":
    main()
