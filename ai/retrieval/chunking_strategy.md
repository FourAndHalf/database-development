# Chunking Strategy

This document defines how we segment long academic PDFs into digestible pieces for the embedding model and LLM.

## The Challenge of Academic Papers
Academic papers are not continuous prose. They contain:
- Multi-column layouts
- Mathematical proofs and pseudocode blocks
- Floating figures and tables
- Extensive reference sections

Standard character-based splitting (e.g., split every 1000 characters) destroys semantic meaning. A split happening in the middle of a Raft pseudocode block renders the chunk useless.

## Our Approach: Semantic Boundary Detection

### 1. Pre-Processing Cleanup
Before chunking, the `pdf_parser.py` removes:
- Page numbers and running headers/footers.
- The `References` section (to avoid polluting the vector space with author names and other paper titles).

### 2. Primary Strategy: Section-Based Chunking
We attempt to split the document based on Markdown-style headers detected during parsing (e.g., "3. System Architecture", "4.1 Data Model").

### 3. Secondary Strategy: Recursive Character Splitting
If a section is larger than our token limit, we fall back to a recursive character text splitter.
- **Target Size:** 512 tokens.
- **Overlap:** 50 tokens (to ensure context isn't lost across boundaries).
- **Separators:** `["\n\n", "\n", ".", " ", ""]` (Attempts to split on paragraphs first, then sentences, then words).

### 4. Contextual Header Injection
**CRITICAL:** The biggest issue with chunks is loss of global context. A chunk reading "The master node fails..." is ambiguous.
Therefore, we prepend every chunk with its lineage:
`[Paper: Google File System (2003)] [Section: 3.2 Master Operation]`
`The master node fails...`

This ensures the embedder maps the chunk to the correct cluster in the vector space.

### 5. Structured JSON Output Format
When chunks are finalized and saved (e.g., to `/data/chunks/`), they MUST be structured in the following standardized JSON format to ensure metadata is strictly coupled with the text content for downstream indexing and retrieval:

```json
{
  "paper": "Dynamo",
  "section": "Architecture",
  "subsection": "Partitioning",
  "content": "The master node fails...",
  "concepts": [
    "consistent hashing",
    "partitioning"
  ]
}
```
This precise JSON structure allows the system to filter by concepts and maintain strict references to the originating paper and section.