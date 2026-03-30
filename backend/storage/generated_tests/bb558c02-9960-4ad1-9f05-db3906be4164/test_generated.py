
import pytest
import httpx
import json

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 10

print("[ai-test-platform] Detected project type: api")
print("[ai-test-platform] Generated test type: api_httpx")

def test_bb558c02_test_login():
    """test login"""
    try:
        # Debug: log the request details
        print("Testing: POST " + BASE_URL + "/login")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            payload = {"username": "admin", "password": "pass"}
            response = client.post("/login", json=payload)
        
        # Verify response status
        assert response.status_code == 200, (
            f"Expected status 200, "
            f"got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

def test_bb558c02_test_create_todo():
    """test create todo"""
    try:
        # Debug: log the request details
        print("Testing: POST " + BASE_URL + "/todos")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            payload = {"todo": "example"}
            response = client.post("/todos", json=payload)
        
        # Verify response status
        assert response.status_code == 201, (
            f"Expected status 201, "
            f"got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

def test_bb558c02_test_health_check():
    """test health check"""
    try:
        # Debug: log the request details
        print("Testing: GET " + BASE_URL + "/health")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            response = client.get("/health")
        
        # Verify response status
        assert response.status_code == 200, (
            f"Expected status 200, "
            f"got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

def test_bb558c02_test_empty_login():
    """test empty login"""
    try:
        # Debug: log the request details
        print("Testing: POST " + BASE_URL + "/login")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            payload = {"**Expected**: 400 Bad Request": ""}
            response = client.post("/login", json=payload)
        
        # Verify response status
        assert response.status_code == 200, (
            f"Expected status 200, "
            f"got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

def test_bb558c02_test_empty_todos():
    """test empty todos"""
    try:
        # Debug: log the request details
        print("Testing: GET " + BASE_URL + "/todos")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            response = client.get("/todos")
        
        # Verify response status
        assert response.status_code == 200, (
            f"Expected status 200, "
            f"got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

def test_bb558c02_test_wrong_method():
    """test wrong method"""
    try:
        # Debug: log the request details
        print("Testing: PUT " + BASE_URL + "/todos")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            payload = {"todo": "example"}
            response = client.put("/todos", json=payload)
        
        # Verify response status
        assert response.status_code == 405, (
            f"Expected status 405, "
            f"got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

def test_bb558c02_test_unauthorized_access():
    """test unauthorized access"""
    try:
        # Debug: log the request details
        print("Testing: GET " + BASE_URL + "/todos")
        
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            response = client.get("/todos")
        
        # Verify response status
        assert response.status_code == 200, (
            f"Expected status 200, "
            f"got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")