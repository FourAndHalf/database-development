# Data Processing Pipeline

This document details the step-by-step pipeline for transforming raw academic PDFs into structured, queryable data for the RAG system.

## Stage 1: Document Acquisition
1. **Source:** PDFs are placed in `/data/raw_pdfs/` or downloaded via `scripts/download_files.py`.
2. **Validation:** Ensure files are valid PDFs. Skip corrupted files.
3. **Metadata Extraction:** Attempt to extract Title, Authors, and Publication Year using basic metadata parsing or an initial LLM pass.

## Stage 2: Docling Preprocessing & Extraction (`services/ingestion/pdf_parser.py`)
1. **Docling Conversion:** Use Docling as the primary parser to convert PDFs into structured document representations.
2. **Layout Analysis:** Preserve columns, headers, section boundaries, references, and page anchors; strip boilerplate (running headers/page numbers) before chunking.
3. **Table Handling:** Extract tables as structured markdown/JSON where possible; fall back to cleaned text for complex tables.
4. **Output:** A normalized JSON object per paper (pages, sections, metadata, citations) saved to `/data/parsed/`.

## Stage 3: Semantic Chunking (`services/ingestion/chunker.py`)
1. **Strategy:** Build chunks from Docling-normalized sections using a Recursive Character Text Splitter or semantic boundary detection.
2. **Parameters:** Target chunk size: 512 tokens. Overlap: 50-100 tokens.
3. **Context Preservation:** Append the paper's title and section header to the beginning of each chunk to ensure the embedder captures the global context.
   - Example contextual format: `[Paper: Spanner (2012)] [Section: TrueTime] The TrueTime API...`
4. **Output:** A list of structured JSON chunk objects. Saved to `/data/chunks/`.
   - Example JSON format: `{ "section": "Architecture", "subsection": "Partitioning", "content": "....", "paper": "Dynamo", "concepts": ["consistent hashing", "partitioning"] }`

## Stage 4: Embedding Generation (`services/ingestion/embedder.py`)
1. **Model Selection:** Load the designated embedding model.
2. **Batching:** Process chunks in batches (e.g., 64 or 128) to maximize GPU/CPU utilization.
3. **Execution:** Generate vectors for each chunk.
4. **Output:** Vectors linked to their corresponding chunk IDs. Saved temporarily to `/data/embeddings/` or streamed directly to the Vector Store.

## Stage 5: Indexing
1. **Vector Index:** Upsert the embeddings and metadata into OpenSearch/Pinecone.
2. **Keyword Index:** Upsert the raw text chunks into an inverted index (e.g., OpenSearch text field) for BM25 search.
3. **Verification:** Run a sanity check script to ensure the number of chunks in the database matches the number of generated chunks.
