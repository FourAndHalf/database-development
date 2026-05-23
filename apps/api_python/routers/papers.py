from fastapi import APIRouter, HTTPException
from apps.api_python_python import state

router = APIRouter()

@router.delete("/papers/{filename}")
async def delete_paper(filename: str):
    """Deletes all chunks associated with a specific PDF filename from the vector database."""
    if not state.retriever or not state.retriever.collection:
        raise HTTPException(status_code=503, detail="Vector database not initialized.")
    
    try:
        # ChromaDB allows deleting by metadata matches
        state.retriever.collection.delete(where={"source": filename})
        print(f"Deleted vectors for source: {filename}")
        return {"status": "success", "deleted": filename}
    except Exception as e:
        print(f"Error deleting vectors for {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
