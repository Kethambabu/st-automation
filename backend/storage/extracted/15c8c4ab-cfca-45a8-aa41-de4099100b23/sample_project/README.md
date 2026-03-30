# Sample Project for AI Test Platform

This sample project is designed to be uploaded to the AI Test Platform for testing.

## What is included

- `app.py`: FastAPI app with `/health`, `/items/{item_id}`, and `/items` endpoints.
- `test_spec.md`: Markdown test spec for the platform (uses h3 headers and **Endpoint** format).
- `requirements.txt`: Python dependencies for the sample service.

## Quick Start (5 steps, ~5 minutes)

### 1. Start Sample App (Terminal 1)

```bash
cd sample_project
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 9000 --reload
```

**Expected**: Logs show "Application startup complete"

### 2. Test Sample App Locally

```bash
curl http://127.0.0.1:9000/health
# Expected: {"status":"ok"}

curl http://127.0.0.1:9000/items/1
# Expected: {"id":1,"name":"Widget","description":"A useful widget."}
```

### 3. Upload & Execute via API

In Python or using curl:

```bash
# Upload ZIP
curl -X POST http://127.0.0.1:8000/api/v1/upload/zip \
  -F file=@sample_project.zip \
  -F project_name="Sample Project"

# Copy PROJECT_ID from response, then execute tests with target_base_url pointing to sample app
curl -X POST http://127.0.0.1:8000/api/v1/tests/execute/{PROJECT_ID} \
  -H "Content-Type: application/json" \
  -d '{
    "markdown_content": "<contents of test_spec.md>",
    "target_base_url": "http://127.0.0.1:9000"
  }'
```

### 4. Check Results

```bash
curl http://127.0.0.1:8000/api/v1/tests/{PROJECT_ID}
```

### 5. Verify

✅ Expected: 4 tests should all **PASS**

---

## Key Points 🎯

- ✅ **Markdown Format**: Uses h3 headers (`### Test Name`) and `**Endpoint**: METHOD /path` format
- ✅ **Target URL**: Pass `target_base_url: "http://127.0.0.1:9000"` when executing (NOT port 8000)
- ✅ **No /api/v1 suffix**: Sample app doesn't have `/api/v1` prefix, use endpoints as-is
- ✅ **All endpoints exist**: /health, /items/{id}, POST /items are all implemented

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 404 errors | Ensure `target_base_url` is `http://127.0.0.1:9000` (not 8000) |
| 422 validation errors | Check POST input JSON format |
| Tests not found | Verify markdown uses h3 headers (`###`), not h2 (`##`) |
| App won't start | Check port 9000 isn't in use; use `lsof -i :9000` or `netstat -ano \|findstr :9000` |

---

## Endpoints Reference

| Method | Endpoint | Status | Input |
|--------|----------|--------|-------|
| GET | /health | 200 | None |
| GET | /items/1 | 200 | None |
| GET | /items/999 | 404 | None |
| POST | /items | 200/400 | `{"id":3,"name":"...","description":"..."}` |

---

## How It Works ✅

**Test Config Default**: `http://127.0.0.1:8000` (no `/api/v1`)
**Sample App Endpoints**: `/health`, `/items/1`, `/items` (at root)
**Test Markdown**: `**Endpoint**: GET /health` (plain paths)
**Built URL**: `http://127.0.0.1:8000/health` ✅ Matches!

This approach allows:
- ✅ Testing apps without `/api/v1` prefix
- ✅ Testing apps WITH `/api/v1` by adding it to endpoints
- ✅ Custom target URLs via `target_base_url` parameter

## Full Documentation

See `E2E_TESTING_GUIDE.md` in the parent directory for complete testing instructions.

