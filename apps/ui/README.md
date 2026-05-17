# UI (Angular) — Chat Mockup

Chat-style UI (ChatGPT/Gemini-ish) wired to the mock Go API in `apps/api`.

## Run

```bash
cd apps/ui
npm install
npm start
```

This uses `proxy.conf.json` so the UI can call the backend at `http://localhost:8080` without CORS issues.

## Notes
- Backend endpoint: `POST /v1/chat`
- Update API base/proxy as you evolve the backend.

