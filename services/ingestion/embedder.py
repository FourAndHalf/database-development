from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np
import torch

class Embedder:
    """
    A high-level wrapper for a Sentence-Transformers model that handles
    generating dense vector embeddings for text.
    """

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        """
        Initializes the Embedder with a specified Sentence-Transformers model.

        Args:
            model_name: The name of the model to load from Hugging Face.
        """
        self.model_name = model_name
        
        # Determine if a GPU is available and set the device accordingly.
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading embedding model: {self.model_name} on device: {self.device}")
        
        # Load the pre-trained model. On first run, this will download the model.
        self.model = SentenceTransformer(self.model_name, device=self.device)
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"Model loaded. Embedding dimension: {self.dimension}")

    def embed_text(self, text: str) -> List[float]:
        """
        Generates an embedding for a single piece of text.

        Args:
            text: The input string to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        # The model's encode function can handle single strings directly.
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a list of texts in an efficient batch.

        Args:
            texts: A list of strings to embed.

        Returns:
            A list of lists of floats, representing the embedding vectors.
        """
        print(f"Generating embeddings for a batch of {len(texts)} texts...")
        
        # The `encode` method is highly optimized for batch processing.
        embeddings = self.model.encode(
            texts, 
            batch_size=32,          # Process 32 texts at a time
            show_progress_bar=True, # Display a progress bar for large batches
            normalize_embeddings=True # Crucial for cosine similarity search
        )
        
        return embeddings.tolist()

if __name__ == "__main__":
    # Example usage to demonstrate the real embedder
    print("Running REAL Embedder example...")
    embedder = Embedder()
    
    sample_text = "Bigtable is a distributed storage system for structured data."
    vector = embedder.embed_text(sample_text)
    
    print(f"\nSample text: {sample_text}")
    print(f"Vector length: {len(vector)}")
    print(f"Vector preview (first 5): {vector[:5]}")
    
    batch_texts = [
        "Dynamo: Amazon's Highly Available Key-value Store", 
        "Consistency models in distributed systems"
    ]
    batch_vectors = embedder.embed_batch(batch_texts)
    print(f"\nBatch processing for {len(batch_vectors)} texts successful.")
    print(f"First vector preview: {batch_vectors[0][:5]}")
