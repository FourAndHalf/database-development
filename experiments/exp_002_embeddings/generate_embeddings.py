import json
import logging
import os
import time
import random
from pathlib import Path
from typing import List, Dict, Any

from docling.datamodel.document import DoclingDocument
from docling.chunking import HierarchicalChunker
import tiktoken

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
EMBEDDING_DIM = 1536
BATCH_SIZES = [10, 50, 100]

def mock_embedding_api(texts: List[str]) -> List[List[float]]:
    """
    Mocks the OpenAI text-embedding-3-small API by generating random vectors 
    and simulating network latency.

    Args:
        texts: A list of text strings to embed.

    Returns:
        A list of embedding vectors (lists of floats).
    """
    # Simulate network latency proportional to batch size
    time.sleep(0.1 + (len(texts) * 0.005))
    
    embeddings = []
    for _ in texts:
        # Generate a random 1536-dimensional vector
        vec = [random.uniform(-1, 1) for _ in range(EMBEDDING_DIM)]
        # Normalize the vector (as OpenAI embeddings are normalized)
        norm = sum(v**2 for v in vec) ** 0.5
        normalized_vec = [v/norm for v in vec]
        embeddings.append(normalized_vec)
        
    return embeddings

def process_documents(input_dir: Path, output_dir: Path) -> None:
    """
    Loads parsed documents, chunks them, generates mock embeddings in batches,
    and evaluates processing efficiency.

    Args:
        input_dir: Path to directory containing Docling JSON files.
        output_dir: Path to directory to save the output chunks and embeddings.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    chunker = HierarchicalChunker()
    encoder = tiktoken.get_encoding("cl100k_base") # text-embedding-3-small uses cl100k_base
    
    all_chunks_text = []
    chunk_metadata = []
    
    json_files = list(input_dir.glob("*.json"))
    if not json_files:
        logger.warning(f"No JSON files found in {input_dir}")
        return
        
    for json_path in json_files:
        logger.info(f"Loading and chunking {json_path.name}...")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                doc_dict = json.load(f)
                
            doc = DoclingDocument.model_validate(doc_dict)
            chunks = list(chunker.chunk(doc))
            
            for i, chunk in enumerate(chunks):
                all_chunks_text.append(chunk.text)
                chunk_metadata.append({
                    "doc_id": json_path.stem,
                    "chunk_idx": i,
                    "text": chunk.text
                })
                
        except Exception as e:
            logger.error(f"Failed to process {json_path.name}: {e}")
            
    logger.info(f"Total chunks extracted: {len(all_chunks_text)}")
    
    # Evaluate batch processing efficiency
    for batch_size in BATCH_SIZES:
        logger.info(f"--- Testing Batch Size: {batch_size} ---")
        
        total_tokens = 0
        start_time = time.time()
        
        for i in range(0, len(all_chunks_text), batch_size):
            batch_texts = all_chunks_text[i:i + batch_size]
            
            # Count tokens
            for text in batch_texts:
                total_tokens += len(encoder.encode(text))
                
            # Generate embeddings
            _ = mock_embedding_api(batch_texts)
            
        end_time = time.time()
        duration = end_time - start_time
        tokens_per_second = total_tokens / duration if duration > 0 else 0
        
        logger.info(f"Batch Size {batch_size}: Processed {total_tokens} tokens in {duration:.2f}s "
                    f"({tokens_per_second:.2f} tokens/sec)")
                    
    # Generate final embeddings (using batch size 50) and save
    logger.info("Generating final embeddings to save...")
    final_embeddings = []
    for i in range(0, len(all_chunks_text), 50):
        batch_texts = all_chunks_text[i:i + 50]
        batch_embeds = mock_embedding_api(batch_texts)
        final_embeddings.extend(batch_embeds)
        
    # Combine chunks and embeddings
    output_data = []
    for meta, emb in zip(chunk_metadata, final_embeddings):
        meta["embedding"] = emb
        output_data.append(meta)
        
    output_file = output_dir / "embedded_chunks.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False)
        
    logger.info(f"Saved {len(output_data)} embedded chunks to {output_file}")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    input_dir = project_root / "experiments" / "exp_001_chunking" / "results"
    output_dir = project_root / "experiments" / "exp_002_embeddings" / "results"
    
    # Create the base experiment directory if it doesn't exist
    (project_root / "experiments" / "exp_002_embeddings").mkdir(parents=True, exist_ok=True)
    
    process_documents(input_dir, output_dir)
