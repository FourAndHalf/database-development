# Apps

This repo uses `apps/` for runnable entrypoints.

## Go API

```bash
cd apps/api
go run ./cmd/api
```

## Angular UI

```bash
cd apps/ui
npm install
npm start
```

The UI proxies `/v1/*` to `http://localhost:8080` via `apps/ui/proxy.conf.json`.

