from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import os
from pathlib import Path
from typing import Any, Dict, List
from dotenv import load_dotenv

import numpy as np

# Allow running this file directly (python services/ingestion/chunker.py).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Docling imports for reading the parsed documents and chunking them.
from docling.datamodel.document import DoclingDocument
from docling.chunking import HierarchicalChunker

from services.ingestion.embedder import Embedder

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DocumentChunker:
    """
    Chunks a parsed DoclingDocument into semantic pieces suitable for 
    embedding and ingestion into a Vector Store, following the project's
    chunking strategy.
    """
    
    def __init__(
        self,
        output_dir: Path,
        target_tokens: int = 512,
        overlap_ratio: float = 0.15,
        min_tokens: int = 64,
        breakpoint_percentile: int = 15,
    ):
        """
        Initializes the DocumentChunker.

        Args:
            output_dir: The directory where the chunked JSON files will be saved.
            target_tokens: Soft upper bound on tokens per semantic sub-chunk.
            overlap_ratio: Fraction of target_tokens carried over from the
                previous sub-chunk (0.15 -> ~15% overlap).
            min_tokens: A sub-chunk smaller than this is not split off early.
            breakpoint_percentile: Consecutive-sentence similarities below this
                percentile are treated as semantic boundaries.
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.target_tokens = target_tokens
        self.overlap_ratio = overlap_ratio
        self.min_tokens = min_tokens
        self.breakpoint_percentile = breakpoint_percentile

        # The HierarchicalChunker intelligently splits based on the document's
        # internal structure (headings, lists, tables) discovered by Docling.
        # We then refine each structural chunk by semantic similarity below.
        self.chunker = HierarchicalChunker()
        # bge-m3 — also used to find semantic boundaries between sentences.
        self.embedder = Embedder()

    def _count_tokens(self, text: str) -> int:
        """Counts model tokens for a piece of text (bge-m3 tokenizer)."""
        return len(self.embedder.model.tokenizer.encode(text, add_special_tokens=False))

    def _semantic_split(self, text: str) -> List[str]:
        """
        Splits a single structural chunk into semantically coherent sub-chunks
        with token-budgeted boundaries and ~overlap_ratio overlap. Never crosses
        the boundaries of the structural chunk it was given.
        """
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        if len(sentences) <= 1:
            return [text.strip()] if text.strip() else []

        token_counts = [self._count_tokens(s) for s in sentences]
        embeddings = np.array(self.embedder.embed_batch(sentences))
        # Embeddings are normalized, so dot product == cosine similarity.
        sims = [float(np.dot(embeddings[i], embeddings[i + 1])) for i in range(len(sentences) - 1)]
        threshold = float(np.percentile(sims, self.breakpoint_percentile)) if sims else 0.0

        # 1. Group sentences into segments at semantic shifts / size limits.
        segments: List[List[str]] = []
        current: List[str] = []
        current_tokens = 0
        for i, sentence in enumerate(sentences):
            current.append(sentence)
            current_tokens += token_counts[i]
            is_last = i == len(sentences) - 1
            semantic_break = i < len(sims) and sims[i] < threshold
            size_break = current_tokens >= self.target_tokens
            if is_last or ((semantic_break or size_break) and current_tokens >= self.min_tokens):
                segments.append(current)
                current = []
                current_tokens = 0
        if current:  # merge any tail remainder into the last segment
            segments[-1].extend(current) if segments else segments.append(current)

        # 2. Re-attach ~overlap_ratio of the previous segment's tail sentences.
        budget = int(self.target_tokens * self.overlap_ratio)
        result: List[str] = []
        for idx, seg in enumerate(segments):
            if idx == 0:
                result.append(" ".join(seg))
                continue
            overlap_sents: List[str] = []
            acc = 0
            for s in reversed(segments[idx - 1]):
                t = self._count_tokens(s)
                if acc + t > budget and overlap_sents:
                    break
                overlap_sents.insert(0, s)
                acc += t
            result.append(" ".join(overlap_sents + seg))
        return result

    def _extract_paper_title(self, doc: DoclingDocument) -> str:
        """Attempts to extract a readable paper title from the document."""
        # 1. Try to get it from Docling's metadata if available
        # Note: Depending on the PDF, this might be empty or inaccurate
        # 2. Fallback: derive from the filename if available
        # For our specific pipeline, filenames are often clean representations of titles.
        # But we don't have direct access to the path from the document object easily 
        # unless we check the name we saved it as, or try to get it from origin.
        title = "Unknown Paper"
        
        # Let's inspect the first element or look for metadata in future versions.
        # Currently, the filename is the safest bet for our curated raw_pdfs.
        return title

    def chunk_document(self, json_path: Path) -> List[Dict[str, Any]]:
        """
        Loads a parsed DoclingDocument from JSON, applies the chunking strategy,
        and saves the resulting structured chunks.
        
        Args:
            json_path: Path to the parsed JSON file.
            
        Returns:
            A list of dictionary representations of the chunks.
        """
        if not json_path.is_file() or json_path.suffix.lower() != '.json':
            logging.warning(f"Skipping non-JSON file: {json_path}")
            return []

        logging.info(f"Chunking document: {json_path}")
        
        try:
            # Load the JSON and validate it back into a DoclingDocument
            doc = DoclingDocument.load_from_json(json_path)
            
            # Use the filename as a proxy for the paper title since we named
            # them cleanly during download.
            paper_title = json_path.stem.replace("_", " ").title()
            
            # Perform the semantic chunking
            raw_chunks = list(self.chunker.chunk(doc))
            
            formatted_chunks = []
            chunk_index = 0

            for chunk in raw_chunks:
                # Extract headings for context injection
                section = "General"
                if hasattr(chunk.meta, 'headings') and chunk.meta.headings:
                    # Often headings looks like "1. INTRODUCTION". We could clean it,
                    # but keeping it raw is safer for context.
                    section = chunk.meta.headings[0]

                # Refine the structural chunk into semantic sub-chunks with overlap.
                for sub_text in self._semantic_split(chunk.text):
                    # Contextual Header Injection as per Strategy Step 4
                    contextual_header = f"[Paper: {paper_title}] [Section: {section}]\n"
                    full_content = contextual_header + sub_text

                    # Construct the strictly required JSON format
                    chunk_data = {
                        "chunk_id": f"{json_path.stem}_chunk_{chunk_index:04d}",
                        "paper": paper_title,
                        "section": section,
                        # We might not have a reliable subsection without deeper analysis
                        # of the headings hierarchy, so we use a default for now.
                        "subsection": "",
                        "content": full_content,
                        # Concepts extraction is typically done by an LLM pass or
                        # specific NLP entity extraction. We leave an empty list
                        # to fulfill the schema contract for now.
                        "concepts": []
                    }

                    formatted_chunks.append(chunk_data)
                    chunk_index += 1

            # Save the formatted chunks to the output directory
            output_file = self.output_dir / f"{json_path.stem}_chunks.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(formatted_chunks, f, indent=2)
                
            logging.info(f"Successfully generated {len(formatted_chunks)} chunks and saved to {output_file}")
            return formatted_chunks
            
        except Exception as e:
            logging.error(f"Failed to chunk {json_path}. Error: {e}")
            return []

def main():
    """
    Main tool entry point. Allows chunking a single parsed file or a batch directory.
    """
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Tool for semantic chunking of parsed Docling JSON documents."
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--file",
        type=Path,
        help="Path to a single parsed JSON file to chunk.",
    )
    group.add_argument(
        "--input-dir",
        type=Path,
        help="Directory containing parsed JSON files for batch processing.",
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/chunks"),
        help="Directory where the chunked JSON files will be saved (default: data/chunks).",
    )
    
    args = parser.parse_args()
    
    chunk_dir = args.output_dir.resolve()
    chunker = DocumentChunker(output_dir=chunk_dir)
    
    if args.file:
        file_path = args.file.resolve()
        if not file_path.exists():
            logging.error(f"Input file not found: {file_path}")
            sys.exit(1)
        logging.info(f"Starting single-file chunking for '{file_path}'...")
        chunker.chunk_document(file_path)
        
    elif args.input_dir:
        parsed_dir = args.input_dir.resolve()
        if not parsed_dir.exists():
            logging.error(f"Input directory not found: {parsed_dir}")
            sys.exit(1)
            
        logging.info(f"Starting batch document chunking process from '{parsed_dir}'...")
        json_files = list(parsed_dir.glob("*.json"))
        
        if not json_files:
            logging.warning(f"No JSON files found in {parsed_dir}.")
            return

        for json_path in json_files:
            chunker.chunk_document(json_path)

    logging.info("Document chunking process completed.")

if __name__ == "__main__":
    main()