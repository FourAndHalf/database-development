import json
from pathlib import Path
from docling.datamodel.document import DoclingDocument
from docling.chunking import HierarchicalChunker

json_path = Path("experiments/exp_001_chunking/results/dynamo_amazons_highly_available_key_value_store.json")
with open(json_path, "r") as f:
    doc_dict = json.load(f)

doc = DoclingDocument.model_validate(doc_dict)
chunker = HierarchicalChunker()
chunks = list(chunker.chunk(doc))

print(f"Generated {len(chunks)} chunks.")
if chunks:
    print(f"First chunk text: {chunks[0].text[:100]}")
