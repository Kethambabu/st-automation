# Sample Todo API

A simple FastAPI-based Todo API perfect for testing the AI Test Generation Platform.

## 📋 Overview

This is a minimal yet complete API with:
- ✅ Multiple HTTP methods (GET, POST, PUT, DELETE)
- ✅ Path parameters and query parameters  
- ✅ Request/response payloads
- ✅ Error handling (404 errors)
- ✅ Different status codes (200, 201, 204, 404)
- ✅ Real-world business logic (Todo CRUD)

Perfect for validating that the AI Test Generation Platform can:
1. Detect the FastAPI entry point
2. Auto-start the server
3. Generate comprehensive test cases
4. Execute tests successfully

## 🚀 Quick Start

### Option 1: Upload to the Platform (RECOMMENDED)

**You DO NOT need to manually run this project.** The AI Test Generation Platform will:

1. ✅ Detect the FastAPI entry point automatically
2. ✅ Start the server on a dynamic port (e.g., 55020)
3. ✅ Generate tests based on the markdown specification
4. ✅ Execute tests against the running server
5. ✅ Collect results and save to database
6. ✅ Shut down the server automatically

**Steps:**
1. Go to the Streamlit UI (`http://localhost:8501`)
2. Click **"🚀 Project Upload"** tab
3. Zip this entire folder: `sample_project.zip`
4. Upload the ZIP file
5. View the dashboard - tests will run automatically
6. Check results in **"📊 Dashboard"** tab

### Option 2: Manual Testing (For Verification Only)

If you want to manually verify the API works:

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python -m uvicorn main:app --host 127.0.0.1 --port 8001

# In another terminal, test endpoints
curl http://localhost:8001/health
curl http://localhost:8001/todos
curl -X POST http://localhost:8001/todos \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "description": "Test todo"}'
```

## 📊 API Endpoints

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| GET | `/health` | 200 | Health check |
| GET | `/todos` | 200 | List all todos |
| GET | `/todos/{id}` | 200/404 | Get specific todo |
| POST | `/todos` | 201 | Create new todo |
| PUT | `/todos/{id}` | 200/404 | Update todo |
| DELETE | `/todos/{id}` | 204/404 | Delete todo |
| GET | `/stats` | 200 | Get statistics |
| GET | `/info` | 200 | Get API info |

## 📝 Test Specification

See `TEST_SPEC.md` for example test cases. The AI platform will use this to generate comprehensive pytest tests.

## 🎯 Expected Test Results

When you upload and process this project, the platform should:

```
✅ Auto-detect FastAPI entry point: main:app
✅ Start server on dynamic port: 55020 (varies)
✅ Generate 8 test cases from specification
✅ Execute all tests
✅ Results:
   - Health check: PASS ✓
   - Get todos: PASS ✓
   - Get todo by ID: PASS ✓
   - 404 handling: PASS ✓
   - Create todo: PASS ✓
   - Update todo: PASS ✓
   - Statistics: PASS ✓
   - API info: PASS ✓
✅ Save results to database
✅ Cleanup: Server automatically terminated
```

## 🔍 What Gets Tested

✔ **HTTP Methods:** GET, POST, PUT, DELETE
✔ **Status Codes:** 200, 201, 204, 404
✔ **Request Payloads:** JSON body in POST/PUT
✔ **Query Parameters:** GET /todos?completed=true
✔ **Path Parameters:** GET /todos/{todo_id}
✔ **Error Handling:** 404 on missing resources
✔ **Response Validation:** Status code assertions

## 🛠️ Dependencies

- FastAPI 0.104.1
- Uvicorn 0.24.0
- Pydantic 2.5.0

All dependencies are listed in `requirements.txt`.

## ❓ FAQ

**Q: Do I need to run this project manually?**
> **A: NO!** The AI Test Generation Platform will start it automatically when you upload it.

**Q: Why is the server on port 8001 in the code?**
> **A: Just a default.** The platform will use a dynamic port (55020, 55021, etc.) to avoid conflicts.

**Q: Can I modify this API?**
> **A: Yes!** Add more endpoints, change business logic, or rename fields. The platform will adapt automatically.

**Q: What if the tests fail?**
> **A:** Check the platform's execution logs. Common issues:
> - Missing dependencies in requirements.txt
> - Invalid entry point (not main:app)
> - Syntax errors in main.py

**Q: Can I use this as a template?**
> **A: Yes!** Copy this folder and replace main.py with your own API.

## 📚 Learn More

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

---

**Ready to test?** Upload this to the AI Test Generation Platform and watch it work! 🚀
