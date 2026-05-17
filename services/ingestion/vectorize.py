import chromadb
import os
import json
from tqdm import tqdm
import textwrap

# --- (Code from lines 1-3 continues here) ---

from embedder import Embedder # Assuming same-directory import

# --- Configuration ---
# Path to the directory where ChromaDB will store its data.
DB_PATH = "data/chromadb"
# Name of the collection to store the embeddings in.
COLLECTION_NAME = "database_papers"
# Directory containing the parsed JSON files.
INPUT_DATA_DIR = "data/parsed"

class Vectorizer:
    """
    Handles the vectorization pipeline:
    1. Loads parsed documents.
    2. Chunks the documents into smaller text segments.
    3. Embeds the text chunks into vectors.
    4. Stores the chunks, embeddings, and metadata in a ChromaDB collection.
    """

    def __init__(self):
        """Initializes the Embedder and ChromaDB client."""
        # Initialize the mock embedder.
        self.embedder = Embedder()
        
        # Initialize the ChromaDB client.
        self.client = chromadb.PersistentClient(path=DB_PATH)
        
        # Get or create the collection.
        self.collection = self.client.get_or_create_collection(name=COLLECTION_NAME)
        print(f"ChromaDB collection '{COLLECTION_NAME}' loaded/created.")

    def chunk_text(self, text, chunk_size=512, chunk_overlap=50):
        """
        Splits a text into overlapping chunks.
        """
        # Use textwrap to split text into lines of a specified width.
        chunks = textwrap.wrap(text, width=chunk_size, break_long_words=False, replace_whitespace=False)
        
        # Re-introduce overlap
        overlapped_chunks = []
        for i in range(len(chunks) - 1):
            # Append the end of the current chunk to the start of the next one
            chunk = chunks[i] + " " + chunks[i+1][:chunk_overlap]
            overlapped_chunks.append(chunk)
        overlapped_chunks.append(chunks[-1]) # Add the last chunk
        
        return overlapped_chunks
        
    def vectorize_and_store(self):
        """
        Main method to process all JSON files and store them in ChromaDB.
        """
        print(f"Starting vectorization process for documents in: {INPUT_DATA_DIR}")
        
        files_to_process = [f for f in os.listdir(INPUT_DATA_DIR) if f.endswith('.json')]
        
        if not files_to_process:
            print("No JSON files found to process. Exiting.")
            return

        for filename in tqdm(files_to_process, desc="Vectorizing Documents"):
            file_path = os.path.join(INPUT_DATA_DIR, filename)
            
            with open(file_path, 'r') as f:
                data = json.load(f)

            # The parsed JSON is a DoclingDocument. The text content is in a list
            # under the 'texts' key, where each item has a 'text' field.
            text_parts = [item.get("text", "") for item in data.get("texts", [])]
            content = "\n".join(text_parts)

            if not content:
                print(f"Warning: No text content found in {filename}. Skipping.")
                continue

            # 1. Chunk the document content.
            chunks = self.chunk_text(content)
            
            # 2. Embed the chunks.
            embeddings = self.embedder.embed_batch(chunks)
            
            # 3. Prepare data for ChromaDB.
            ids = [f"{filename}-{i}" for i in range(len(chunks))]
            metadatas = [{"source": filename, "chunk_number": i} for i in range(len(chunks))]

            # 4. Add to the ChromaDB collection.
            self.collection.add(
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            
        print("\nVectorization complete!")
        print(f"Total documents processed: {len(files_to_process)}")
        print(f"Total entries in collection: {self.collection.count()}")

if __name__ == "__main__":
    vectorizer = Vectorizer()
    vectorizer.vectorize_and_store()
