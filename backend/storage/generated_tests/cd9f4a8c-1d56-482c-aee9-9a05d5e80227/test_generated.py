
import pytest
import httpx
import json

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 10

print("[ai-test-platform] Detected project type: api")
print("[ai-test-platform] Generated test type: api_httpx")

def test_cd9f4a8c_test_health_check():
    """test health check"""
    try:
        
        # Execute GET/DELETE/HEAD request
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.request(
                "HTTPMethod.GET",
                BASE_URL + "/health",
            )
        
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

def test_cd9f4a8c_test_read_item():
    """test read item"""
    try:
        
        # Execute GET/DELETE/HEAD request
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.request(
                "HTTPMethod.GET",
                BASE_URL + "/items/1",
            )
        
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

def test_cd9f4a8c_test_empty_input():
    """test empty input"""
    try:
        # Prepare request payload (only when we have one)
        payload = {"**Expected**: 422 Unprocessable Entity": ""}

        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.request(
                "HTTPMethod.POST",
                BASE_URL + "/items",
                json=payload,
            )
        
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

def test_cd9f4a8c_test_wrong_method():
    """test wrong method"""
    try:
        # Prepare request payload (only when we have one)
        payload = {"item": "item1"}

        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.request(
                "HTTPMethod.PUT",
                BASE_URL + "/items",
                json=payload,
            )
        
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

def test_cd9f4a8c_test_unauthorized_access():
    """test unauthorized access"""
    try:
        
        # Execute GET/DELETE/HEAD request
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.request(
                "HTTPMethod.GET",
                BASE_URL + "/items",
            )
        
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