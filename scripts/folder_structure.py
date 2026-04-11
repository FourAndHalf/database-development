import os
from pathlib import Path

# Toggle this if you want to overwrite existing files
OVERWRITE = False

# Create the structure in the repository root (one level above `scripts/`),
# not in a nested `database-development/` directory.
BASE_DIR = Path(__file__).resolve().parents[1]

STRUCTURE = {
    "apps": {
        "api": {},
        "ui": {}
    },
    "services": {
        "ingestion": {
            "pdf_parser.py": "",
            "chunker.py": "",
            "embedder.py": ""
        },
        "retrieval": {
            "vector_store.py": "",
            "hybrid_search.py": "",
            "reranker.py": ""
        },
        "llm": {
            "prompt_builder.py": "",
            "response_generator.py": ""
        }
    },
    "ai": {
        "system": {
            "system_design.md": "",
            "architecture.md": "",
            "pipeline.md": ""
        },
        "retrieval": {
            "retrieval_strategy.md": "",
            "chunking_strategy.md": "",
            "indexing_strategy.md": "",
            "reranking_strategy.md": ""
        },
        "prompting": {
            "system_prompt.md": "",
            "query_prompt.md": "",
            "answer_prompt.md": "",
            "guardrails.md": ""
        },
        "knowledge": {
            "papers_index.md": "",
            "concepts_map.md": "",
            "taxonomy.md": "",
            "domain_notes": {
                "distributed_systems.md": "",
                "consistency_models.md": ""
            }
        },
        "evaluation": {
            "evaluation.md": "",
            "test_queries.md": "",
            "expected_answers.md": "",
            "metrics.md": "",
            "failure_modes.md": ""
        },
        "memory": {
            "user_patterns.md": "",
            "learned_behaviors.md": ""
        },
        "governance": {
            "rules.md": "",
            "constraints.md": "",
            "versioning.md": ""
        }
    },
    "data": {
        "raw_pdfs": {},
        "parsed": {},
        "chunks": {},
        "embeddings": {}
    },
    "infra": {
        "docker": {},
        "k8s": {},
        "terraform": {}
    },
    "experiments": {
        "exp_001_chunking": {},
        "exp_002_embeddings": {},
        "exp_003_reranking": {},
        "experiments.md": ""
    },
    "scripts": {},
    "README.md": "# RAG System\n"
}


def create_structure(base_path, structure):
    for name, content in structure.items():
        path = os.path.join(base_path, name)

        if isinstance(content, dict):
            # Create directory
            os.makedirs(path, exist_ok=True)
            create_structure(path, content)
        else:
            # Create file
            if not os.path.exists(path) or OVERWRITE:
                with open(path, "w") as f:
                    f.write(content or "")
                print(f"Created file: {path}")
            else:
                print(f"Skipped (exists): {path}")


if __name__ == "__main__":
    print(f"Base dir: {BASE_DIR}")
    create_structure(str(BASE_DIR), STRUCTURE)
    print("\nRAG project structure initialized successfully.")
