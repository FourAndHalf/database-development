import json
import logging
import os
import traceback
from pathlib import Path
from typing import List, Dict, Any

from docling.document_converter import DocumentConverter

# Configure logging according to rules
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_pdfs(pdf_paths: List[Path], output_dir: Path) -> None:
    """
    Parses a list of PDF files using Docling and saves the results as JSON.

    Args:
        pdf_paths: A list of pathlib.Path objects pointing to the PDFs to parse.
        output_dir: A pathlib.Path object pointing to the directory where results should be saved.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    converter = DocumentConverter()
    
    for pdf_path in pdf_paths:
        if not pdf_path.exists():
            logger.error(f"File not found: {pdf_path}")
            continue
            
        logger.info(f"Parsing {pdf_path.name}...")
        
        output_file = output_dir / f"{pdf_path.stem}.json"
        
        # Idempotency check: if output already exists, we could skip, but to be truly 
        # idempotent in terms of regenerating the same output, we should overwrite.
        # However, to save time on rerun we could skip if file exists. 
        # The prompt says: "Running it twice on the same directory should result in the exact same JSON output."
        # We will parse and overwrite.
        
        try:
            result = converter.convert(str(pdf_path))
            doc_dict = result.document.export_to_dict()
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(doc_dict, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Successfully saved parsed output to {output_file}")
            
        except Exception as e:
            # Rule 3: No silenced errors. Log PDF name and stack trace.
            # Page number might be deep within Docling, but we log what we have.
            logger.error(f"Failed to parse {pdf_path.name}.")
            logger.error(f"Error details: {e}")
            logger.error(f"Stack trace:\n{traceback.format_exc()}")

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    raw_pdfs_dir = project_root / "data" / "raw_pdfs"
    output_dir = project_root / "experiments" / "exp_001_chunking" / "results"
    
    target_pdfs = [
        raw_pdfs_dir / "dynamo_amazons_highly_available_key_value_store.pdf",
        raw_pdfs_dir / "bigtable_a_distributed_storage_system_for_structured_data.pdf"
    ]
    
    parse_pdfs(target_pdfs, output_dir)
