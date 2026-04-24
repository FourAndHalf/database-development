from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from docling.document_converter import DocumentConverter
from docling.datamodel.document import DoclingDocument

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

    def parse_pdf(self, pdf_path: Path) -> DoclingDocument | None:
        """
        Parses a single PDF file using Docling, saves the structured
        output as JSON, and returns the parsed DoclingDocument.

        Args:
            pdf_path: The path to the PDF file to parse.

        Returns:
            A DoclingDocument object if parsing is successful, otherwise None.
        """
        if not pdf_path.is_file() or pdf_path.suffix.lower() != '.pdf':
            logging.warning(f"Skipping non-PDF file: {pdf_path}")
            return None

        output_path = self.output_dir / f"{pdf_path.stem}.json"
        if output_path.exists():
            logging.info(f"Parsed file already exists, loading from cache: {output_path}")
            try:
                doc = DoclingDocument.model_validate_json(output_path.read_text(encoding="utf-8"))
                return doc
            except Exception as e:
                logging.error(f"Failed to load cached JSON for {pdf_path}. Reparsing. Error: {e}")

        logging.info(f"Parsing PDF: {pdf_path}")
        try:
            # The core conversion step using the docling library
            doc = self.converter.convert(pdf_path)
            
            # Save the parsed document as a JSON file
            # The model_dump_json method serializes the Pydantic model
            output_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
            logging.info(f"Successfully parsed and saved to {output_path}")
            
            return doc
        except Exception as e:
            logging.error(f"Failed to parse {pdf_path}. Error: {e}")
            return None

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
        default=Path("data/parsed"),
        help="Directory where the parsed JSON files will be saved (default: data/parsed).",
    )
    
    args = parser.parse_args()
    
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
