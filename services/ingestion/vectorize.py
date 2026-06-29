import os
import sys
import json
from tqdm import tqdm

# Allow running this file directly (python services/ingestion/vectorize.py).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.ingestion.embedder import Embedder
from services.retrieval.vector_store import get_vector_store

from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
# Directory containing the chunked JSON files produced by chunker.py.
INPUT_DATA_DIR = os.getenv("LOCAL_CHUNKS_DIR", "data/chunks")


class Vectorizer:
    """
    Handles the vectorization pipeline:
    1. Loads pre-chunked documents (output of chunker.py).
    2. Embeds the chunk content into vectors.
    3. Stores the chunks, embeddings, and metadata in a VectorStore (ChromaDB).
    """

    def __init__(self):
        """Initializes the Embedder and VectorStore."""
        self.embedder = Embedder()
        self.vector_store = get_vector_store()
        print(f"VectorStore initialized.")

    def vectorize_and_store(self):
        """
        Main method to process all chunk JSON files and store them in ChromaDB.
        Chunking already happened in chunker.py; here we only embed + store.
        """
        print(f"Starting vectorization process for chunks in: {INPUT_DATA_DIR}")

        files_to_process = [f for f in os.listdir(INPUT_DATA_DIR) if f.endswith('.json')]

        if not files_to_process:
            print("No chunk JSON files found to process. Run chunker.py first. Exiting.")
            return

        for filename in tqdm(files_to_process, desc="Vectorizing Documents"):
            file_path = os.path.join(INPUT_DATA_DIR, filename)

            with open(file_path, 'r') as f:
                chunks = json.load(f)

            if not chunks:
                print(f"Warning: No chunks found in {filename}. Skipping.")
                continue

            # 1. Pull text + metadata straight from the chunk contract.
            documents = [c["content"] for c in chunks]
            ids = [c["chunk_id"] for c in chunks]
            metadatas = [
                {
                    # "source" is what query/delete filter on; use the paper name.
                    "source": c.get("paper", filename),
                    "section": c.get("section", ""),
                    "subsection": c.get("subsection", ""),
                    # Chroma metadata can't hold lists, so flatten concepts.
                    "concepts": ", ".join(c.get("concepts", [])),
                }
                for c in chunks
            ]

            # 2. Embed the chunk content.
            embeddings = self.embedder.embed_batch(documents)

            # 3. Add to the VectorStore.
            self.vector_store.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

        print("\nVectorization complete!")
        print(f"Total chunk files processed: {len(files_to_process)}")
        print(f"Total entries in collection: {self.vector_store.count()}")

if __name__ == "__main__":
    vectorizer = Vectorizer()
    vectorizer.vectorize_and_store()
