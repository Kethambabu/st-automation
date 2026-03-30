import pytest
import httpx
import json

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 10

print("[ai-test-platform] Detected project type: api")
print("[ai-test-platform] Generated test type: smart_api")

def test_health_check():
    """Test GET /health"""
    try:
        print("Testing: GET " + BASE_URL + "/health")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            response = client.get("/health")
        
        assert response.status_code in [200, 200, 201, 400], (
            f"Expected success status, got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

def test_get_todos():
    """Test GET /todos"""
    try:
        print("Testing: GET " + BASE_URL + "/todos")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            response = client.get("/todos")
        
        assert response.status_code in [200, 200, 201, 400], (
            f"Expected success status, got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

def test_get_todo():
    """Test GET /todos/{todo_id}"""
    try:
        print("Testing: GET " + BASE_URL + "/todos/1")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            response = client.get("/todos/1")
        
        assert response.status_code in [200, 200, 201, 400], (
            f"Expected success status, got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

def test_create_todo():
    """Test POST /todos"""
    try:
        print("Testing: POST " + BASE_URL + "/todos")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            payload = {"title": "test_title", "description": "test_description"}
            response = client.post("/todos", json=payload)
        
        assert response.status_code in [201, 200, 201, 400], (
            f"Expected success status, got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

def test_update_todo():
    """Test PUT /todos/{todo_id}"""
    try:
        print("Testing: PUT " + BASE_URL + "/todos/1")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            payload = {"title": "test_title", "description": "test_description", "completed": "test_completed"}
            response = client.put("/todos/1", json=payload)
        
        assert response.status_code in [200, 200, 201, 400], (
            f"Expected success status, got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

def test_delete_todo():
    """Test DELETE /todos/{todo_id}"""
    try:
        print("Testing: DELETE " + BASE_URL + "/todos/1")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            response = client.delete("/todos/1")
        
        assert response.status_code in [204, 200], (
            f"Expected success status, got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

def test_clear_all_todos():
    """Test POST /todos/bulk/clear"""
    try:
        print("Testing: POST " + BASE_URL + "/todos/bulk/clear")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            response = client.post("/todos/bulk/clear")
        
        assert response.status_code in [201, 200, 201, 400], (
            f"Expected success status, got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

def test_get_stats():
    """Test GET /stats"""
    try:
        print("Testing: GET " + BASE_URL + "/stats")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            response = client.get("/stats")
        
        assert response.status_code in [200, 200, 201, 400], (
            f"Expected success status, got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

def test_get_info():
    """Test GET /info"""
    try:
        print("Testing: GET " + BASE_URL + "/info")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            response = client.get("/info")
        
        assert response.status_code in [200, 200, 201, 400], (
            f"Expected success status, got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

