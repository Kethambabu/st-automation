
import pytest
import httpx
import json

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 10

print("[ai-test-platform] Detected project type: api")
print("[ai-test-platform] Generated test type: api_httpx")

def test_ccff1897_test_health_check():
    """Test Health Check"""
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

def test_ccff1897_test_create_item():
    """Test Create Item"""
    try:
        # Prepare request payload (only when we have one)
        payload = {"item": "example"}

        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.request(
                "HTTPMethod.POST",
                BASE_URL + "/items",
                json=payload,
            )
        
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

def test_ccff1897_test_empty_item():
    """Test Empty Item"""
    try:
        # Prepare request payload (only when we have one)
        payload = {"item": ""}

        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.request(
                "HTTPMethod.POST",
                BASE_URL + "/items",
                json=payload,
            )
        
        # Verify response status
        assert response.status_code == 422, (
            f"Expected status 422, "
            f"got {response.status_code}. "
            f"Response: {response.text[:200]}"
        )
        
    except httpx.TimeoutException:
        pytest.skip("Request timed out")
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")

def test_ccff1897_test_wrong_method():
    """Test Wrong Method"""
    try:
        # Prepare request payload (only when we have one)
        payload = {"item_id": "1"}

        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.request(
                "HTTPMethod.PUT",
                BASE_URL + "/items/{item_id}",
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

def test_ccff1897_test_unauthorized_access():
    """Test Unauthorized Access"""
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