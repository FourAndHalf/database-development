from fastapi import APIRouter, HTTPException
from apps.api_python import state

router = APIRouter()

@router.delete("/papers/{filename}")
async def delete_paper(filename: str):
    """Deletes all chunks associated with a specific PDF filename from the vector database."""
    if not state.retriever or not state.retriever.vector_store:
        raise HTTPException(status_code=503, detail="Vector database not initialized.")
    
    try:
        # Use the generic delete method
        state.retriever.vector_store.delete(filename=filename)
        print(f"Deleted vectors for source: {filename}")
        return {"status": "success", "deleted": filename}
    except Exception as e:
        print(f"Error deleting vectors for {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
