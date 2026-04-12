# Rules of Engagement for AI Agents

These are the strict, unbreakable rules for AI coding agents (like Gemini CLI) modifying this codebase.

1. **Test-Driven Modifications:** Never modify the `services/retrieval` logic without first running the evaluation suite. You must prove your change improves NDCG@5 or Recall@5.
2. **Idempotency in Ingestion:** The `services/ingestion/pdf_parser.py` must be completely idempotent. Running it twice on the same directory should result in the exact same JSON output.
3. **No Silenced Errors:** When parsing PDFs, do not use bare `except:` or `pass`. If a table fails to parse, log the exact page number, PDF name, and stack trace using the standard Python `logging` module so we can improve the parser.
4. **Environment Variables Only:** Never hardcode AWS keys, OpenSearch URLs, or LLM API keys. Use `os.getenv()` or a `.env` file via `python-dotenv`.
5. **Type Hinting Required:** All Python code in `/services` and `/apps/api` MUST use strict Type Hinting (PEP 484). We use `mypy` in our CI pipeline.
6. **Documentation Standard:** All new functions must include a Google-style docstring explaining parameters, return types, and potential side-effects.
7. **README and AI Documentation Coherence:** Any time you make architectural, strategic, or structural changes to the project or the `ai/` guardrail documentation, you MUST cross-reference and update the `README.md` to ensure complete coherence. The `README.md` and the `ai/` files must never contradict each other.

**Failure to adhere to these rules will result in rejected Pull Requests.**