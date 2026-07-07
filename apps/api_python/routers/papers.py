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

from fastapi import UploadFile, File
import pypdf
import os
from google import genai
from google.genai import types

@router.post("/papers/validate")
async def validate_paper(file: UploadFile = File(...)):
    """Validates if the uploaded PDF is a research paper."""
    if not file.filename.lower().endswith('.pdf'):
        return {"valid": False, "reason": "Not a PDF"}
        
    try:
        # Read the first page
        reader = pypdf.PdfReader(file.file)
        if len(reader.pages) == 0:
            return {"valid": False, "reason": "Empty PDF"}
            
        first_page = reader.pages[0].extract_text()
        first_page = first_page[:3000] # Limit to 3000 chars
        
        # Reset file pointer for any subsequent reads if needed
        await file.seek(0)
        
        # Ask LLM
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        prompt = f"Given the following text from the first page of a PDF document, determine if this document is likely a research paper, academic article, or scientific publication. Answer with ONLY 'YES' or 'NO'.\n\nText:\n{first_page}"
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        answer = response.text.strip().upper()
        if "YES" in answer:
            return {"valid": True}
        else:
            return {"valid": False, "reason": "The AI determined this is not a research paper."}
            
    except Exception as e:
        print(f"Validation error: {e}")
        # If it fails to parse or call LLM, we can either reject or accept.
        # Let's reject it to be safe, or just return an error.
        raise HTTPException(status_code=500, detail="Failed to validate paper")
