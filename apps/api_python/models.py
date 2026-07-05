from pydantic import BaseModel

class Turn(BaseModel):
    role: str            # 'user' | 'assistant'
    text: str

class QueryRequest(BaseModel):
    query: str
    n_results: int = 5
    model: str = "aether-2.0"
    history: list[Turn] = []

class Source(BaseModel):
    source_file: str
    content: str
    distance: float
    url: str | None = None

class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
