import chromadb
import argparse
import sys
import os

# Add the project root to the Python path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.ingestion.embedder import Embedder

# --- Configuration ---
# Must match the path and collection name used in vectorize.py
DB_PATH = "data/chromadb"
COLLECTION_NAME = "database_papers"

class PaperRetriever:
    """
    Handles querying the ChromaDB collection to retrieve relevant document chunks.
    """

    def __init__(self):
        """Initializes the Embedder and connects to the ChromaDB."""
        # The same mock embedder is used to turn the query into a vector.
        self.embedder = Embedder()
        
        # Connect to the existing persistent database.
        try:
            client = chromadb.PersistentClient(path=DB_PATH)
            # Use get_or_create_collection to ensure the API doesn't crash if the DB is empty
            self.collection = client.get_or_create_collection(name=COLLECTION_NAME)
            print(f"Successfully connected to ChromaDB collection '{COLLECTION_NAME}'.")
            print(f"Total entries in collection: {self.collection.count()}")
        except Exception as e:
            print(f"Error connecting to ChromaDB: {e}")
            self.collection = None

    def query(self, query_text: str, n_results: int = 5):
        """
        Queries the collection for the most relevant chunks to the given text.

        Args:
            query_text: The user's question or query.
            n_results: The number of results to retrieve.
        """
        if not self.collection:
            print("Retriever is not connected to a collection. Cannot query.")
            return

        print(f"\n{'='*20}\n🔍 Querying for: '{query_text}'\n{'='*20}")
        
        # 1. Convert the query text into a vector.
        query_embedding = self.embedder.embed_text(query_text)
        
        # 2. Perform the similarity search in ChromaDB.
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # 3. Process and display the results.
        documents = results.get('documents', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        distances = results.get('distances', [[]])[0]

        if not documents:
            print("No results found.")
            return

        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
            source_file = meta.get('source', 'Unknown')
            # Clean up the document text for better readability
            clean_doc = ' '.join(doc.split())
            
            print(f"\n--- Result {i+1} (Distance: {dist:.4f}) ---")
            print(f"📄 Source: {source_file}")
            print(f"💬 Text: \"{clean_doc}\"")
            
def main():
    """Provides a CLI to query the vector database."""
    parser = argparse.ArgumentParser(description="Query research papers from the ChromaDB vector store.")
    parser.add_argument(
        "query_text",
        type=str,
        help="The question or topic to query for."
    )
    parser.add_argument(
        "-n", "--n_results",
        type=int,
        default=3,
        help="The number of results to return."
    )
    args = parser.parse_args()

    retriever = PaperRetriever()
    if retriever.collection:
        retriever.query(args.query_text, n_results=args.n_results)

if __name__ == "__main__":
    # You can run this script from the command line like so:
    # python3 services/retrieval/query.py "What is the role of a tablet in Bigtable?" -n 3
    
    # Or, to see a few examples, you can comment out main() and uncomment below:
    
    retriever = PaperRetriever()
    if retriever.collection:
        example_queries = [
            "What is Bigtable?",
            "How does the Chubby lock service work?",
            "Explain the CAP theorem",
            "What is a column-family database?"
        ]
        for q in example_queries:
            retriever.query(q, n_results=2)
