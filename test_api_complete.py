#!/usr/bin/env python3
"""
Complete API Test Suite
Comprehensive tests for all API endpoints including the new dynamic API info feature
"""
import requests
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional


def load_api_key() -> str:
    """Load API key from .env file"""
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("Error: .env file not found")
        sys.exit(1)

    with open(env_file) as f:
        for line in f:
            if line.startswith("API_KEY="):
                return line.strip().split("=", 1)[1]

    print("Error: API_KEY not found in .env file")
    sys.exit(1)


# Configuration
SERVER_HOST = sys.argv[1] if len(sys.argv) > 1 else "localhost"
API_BASE_URL = f"http://{SERVER_HOST}:8080"
API_KEY = load_api_key()


def print_test_header(test_num: int, test_name: str):
    """Print formatted test header"""
    print(f"\n{test_num}. {test_name}")
    print("   " + "="*60)


def print_success(message: str):
    """Print success message"""
    print(f"   ✓ {message}")


def print_error(message: str):
    """Print error message"""
    print(f"   ✗ {message}")


def print_info(message: str):
    """Print info message"""
    print(f"   ℹ {message}")


def test_api_info_endpoint() -> bool:
    """Test 1: API Info Endpoint (Dynamic API Key Display)"""
    print_test_header(1, "API Info Endpoint")

    try:
        # Test the new /v1/api/info endpoint
        response = requests.get(f"{API_BASE_URL}/v1/api/info", timeout=5)

        if response.status_code != 200:
            print_error(f"API info endpoint returned status {response.status_code}")
            return False

        data = response.json()

        # Verify structure
        if "api_key" not in data:
            print_error("Response missing 'api_key' field")
            return False

        if "router_port" not in data:
            print_error("Response missing 'router_port' field")
            return False

        # Verify values
        returned_key = data["api_key"]
        returned_port = data["router_port"]

        print_success("API info endpoint accessible without authentication")
        print_info(f"API Key: {returned_key[:20]}...")
        print_info(f"Router Port: {returned_port}")

        # Verify returned key matches our key
        if returned_key == API_KEY:
            print_success("Returned API key matches .env configuration")
        else:
            print_error("Returned API key does not match .env")
            print_info(f"Expected: {API_KEY[:20]}...")
            print_info(f"Got: {returned_key[:20]}...")
            return False

        return True

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_authentication_valid() -> bool:
    """Test 2: Valid API Key Authentication"""
    print_test_header(2, "Valid Authentication")

    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = requests.get(f"{API_BASE_URL}/v1/models", headers=headers, timeout=5)

        if response.status_code == 200:
            print_success("Valid API key accepted")
            models = response.json().get("data", [])
            print_info(f"Found {len(models)} models")
            return True
        else:
            print_error(f"Valid API key rejected with status {response.status_code}")
            return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_authentication_invalid() -> bool:
    """Test 3: Invalid API Key Authentication"""
    print_test_header(3, "Invalid Authentication")

    try:
        # Test with wrong API key
        headers = {"Authorization": "Bearer invalid-key-12345"}
        response = requests.get(f"{API_BASE_URL}/v1/models", headers=headers, timeout=5)

        if response.status_code == 401:
            print_success("Invalid API key properly rejected (401)")
            error_data = response.json()
            if "detail" in error_data or "error" in error_data:
                print_success("Error response includes detail message")
            return True
        else:
            print_error(f"Invalid key returned unexpected status {response.status_code}")
            return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_authentication_missing() -> bool:
    """Test 4: Missing API Key Authentication"""
    print_test_header(4, "Missing Authentication")

    try:
        # Test without Authorization header
        response = requests.get(f"{API_BASE_URL}/v1/models", timeout=5)

        if response.status_code in [401, 403]:
            print_success(f"Missing API key properly rejected ({response.status_code})")
            return True
        else:
            print_error(f"Missing auth returned unexpected status {response.status_code}")
            return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_models_list() -> bool:
    """Test 5: Models List Endpoint"""
    print_test_header(5, "Models List Endpoint")

    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = requests.get(f"{API_BASE_URL}/v1/models", headers=headers, timeout=5)

        if response.status_code != 200:
            print_error(f"Endpoint returned status {response.status_code}")
            return False

        data = response.json()

        # Check structure
        if data.get("object") != "list":
            print_error("Response missing 'object': 'list'")
            return False

        if "data" not in data:
            print_error("Response missing 'data' field")
            return False

        models = data["data"]
        print_success(f"Found {len(models)} running models")

        # Verify model structure
        for model in models:
            required_fields = ["id", "object", "owned_by"]
            missing = [f for f in required_fields if f not in model]
            if missing:
                print_error(f"Model missing fields: {missing}")
                return False
            print_info(f"- {model['id']} (status: {model.get('status', 'unknown')})")

        if len(models) == 0:
            print_info("Note: No models currently running")

        print_success("Models list endpoint working correctly")
        return True

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_models_status() -> bool:
    """Test 6: Model Status Endpoint"""
    print_test_header(6, "Model Status Endpoint")

    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = requests.get(f"{API_BASE_URL}/v1/models/status", headers=headers, timeout=5)

        if response.status_code != 200:
            print_error(f"Endpoint returned status {response.status_code}")
            return False

        data = response.json()

        # Check structure
        if "models" not in data:
            print_error("Response missing 'models' field")
            return False

        if "gpu" not in data:
            print_error("Response missing 'gpu' field")
            return False

        models = data["models"]
        gpu_info = data["gpu"]

        print_success(f"Status retrieved for {len(models)} models")

        # Display GPU info
        if gpu_info:
            print_info(f"GPU Memory: {gpu_info.get('used_gb', 0):.1f}GB used / {gpu_info.get('total_gb', 0):.1f}GB total")
            print_info(f"Available: {gpu_info.get('available_gb', 0):.1f}GB")

        # Count model states
        running = sum(1 for m in models.values() if m.get("status") == "running")
        loading = sum(1 for m in models.values() if m.get("status") == "loading")
        stopped = sum(1 for m in models.values() if m.get("status") in ["exited", "not_found"])
        failed = sum(1 for m in models.values() if m.get("status") == "failed")

        print_info(f"Running: {running}, Loading: {loading}, Stopped: {stopped}, Failed: {failed}")
        print_success("Model status endpoint working correctly")

        return True

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_health_check() -> bool:
    """Test 7: Health Check Endpoint"""
    print_test_header(7, "Health Check Endpoint")

    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)

        if response.status_code != 200:
            print_error(f"Health check returned status {response.status_code}")
            return False

        data = response.json()
        if data.get("status") == "healthy":
            print_success("Router is healthy")
            return True
        else:
            print_error(f"Unexpected health status: {data}")
            return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_chat_completion() -> bool:
    """Test 8: Chat Completion (Non-Streaming)"""
    print_test_header(8, "Chat Completion (Non-Streaming)")

    try:
        # First get available models
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        models_response = requests.get(f"{API_BASE_URL}/v1/models", headers=headers, timeout=5)
        models = models_response.json().get("data", [])

        if not models:
            print_info("No running models available - skipping chat test")
            return True

        model_id = models[0]["id"]
        print_info(f"Testing with model: {model_id}")

        # Send chat completion request
        payload = {
            "model": model_id,
            "messages": [
                {"role": "user", "content": "What is 2+2? Answer with just the number."}
            ],
            "max_tokens": 10,
            "temperature": 0.1,
            "stream": False
        }

        response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            print_error(f"Chat completion failed with status {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        data = response.json()

        # Verify response structure
        required_fields = ["id", "object", "created", "model", "choices", "usage"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            print_error(f"Response missing fields: {missing}")
            return False

        if not data["choices"]:
            print_error("No choices in response")
            return False

        message = data["choices"][0]["message"]
        content = message.get("content") or message.get("reasoning_content", "")

        print_success("Chat completion successful")
        print_info(f"Response: {content[:100]}...")
        print_info(f"Tokens used: {data['usage'].get('total_tokens', 'N/A')}")

        return True

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_chat_completion_streaming() -> bool:
    """Test 9: Chat Completion (Streaming)"""
    print_test_header(9, "Chat Completion (Streaming)")

    try:
        # First get available models
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        models_response = requests.get(f"{API_BASE_URL}/v1/models", headers=headers, timeout=5)
        models = models_response.json().get("data", [])

        if not models:
            print_info("No running models available - skipping streaming test")
            return True

        model_id = models[0]["id"]
        print_info(f"Testing with model: {model_id}")

        # Send streaming chat completion request
        payload = {
            "model": model_id,
            "messages": [
                {"role": "user", "content": "Count: 1, 2, 3"}
            ],
            "max_tokens": 20,
            "temperature": 0.1,
            "stream": True
        }

        response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=30
        )

        if response.status_code != 200:
            print_error(f"Streaming failed with status {response.status_code}")
            return False

        chunks_received = 0
        content_received = ""

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    if line_str == 'data: [DONE]':
                        break
                    try:
                        chunk_data = json.loads(line_str[6:])
                        delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content") or delta.get("reasoning_content", "")
                        if content:
                            content_received += content
                            chunks_received += 1
                    except json.JSONDecodeError:
                        pass

        if chunks_received > 0:
            print_success(f"Streaming successful - Received {chunks_received} chunks")
            print_info(f"Content: {content_received[:50]}...")
            return True
        else:
            print_error("No chunks received in streaming response")
            return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_cors_headers() -> bool:
    """Test 10: CORS Headers"""
    print_test_header(10, "CORS Headers")

    try:
        # Test with Origin header
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Origin": "http://localhost:3000"
        }

        response = requests.get(f"{API_BASE_URL}/v1/models", headers=headers, timeout=5)

        # Check for CORS headers
        cors_headers = {
            "access-control-allow-origin": "*",
            "access-control-allow-methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
        }

        all_present = True
        for header, expected in cors_headers.items():
            actual = response.headers.get(header, "")
            if expected in actual or actual == "*":
                print_success(f"Header '{header}' present")
            else:
                print_error(f"Header '{header}' missing or incorrect")
                all_present = False

        if all_present:
            print_success("All CORS headers present")
            return True
        else:
            return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def test_error_handling() -> bool:
    """Test 11: Error Handling"""
    print_test_header(11, "Error Handling")

    tests_passed = 0
    tests_total = 3

    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        # Test 1: Invalid model name
        print_info("Testing invalid model name...")
        payload = {
            "model": "non-existent-model-xyz",
            "messages": [{"role": "user", "content": "Test"}],
            "max_tokens": 10
        }
        response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code in [400, 404]:
            print_success("Invalid model properly rejected")
            tests_passed += 1
        else:
            print_error(f"Invalid model returned status {response.status_code}")

        # Test 2: Malformed request (missing required field)
        print_info("Testing malformed request...")
        payload = {
            "model": "test-model",
            # Missing 'messages' field
            "max_tokens": 10
        }
        response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 422:
            print_success("Malformed request properly rejected (422)")
            tests_passed += 1
        else:
            print_error(f"Malformed request returned status {response.status_code}")

        # Test 3: Invalid endpoint
        print_info("Testing invalid endpoint...")
        response = requests.get(
            f"{API_BASE_URL}/v1/invalid-endpoint",
            headers=headers,
            timeout=5
        )

        if response.status_code == 404:
            print_success("Invalid endpoint properly rejected (404)")
            tests_passed += 1
        else:
            print_error(f"Invalid endpoint returned status {response.status_code}")

        print_info(f"Error handling: {tests_passed}/{tests_total} tests passed")
        return tests_passed == tests_total

    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


def main():
    """Run all API tests"""
    print("="*70)
    print("COMPLETE API TEST SUITE")
    print("Comprehensive validation of all API endpoints")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Server: {SERVER_HOST}")
    print(f"  API Base URL: {API_BASE_URL}")
    print(f"  API Key: {API_KEY[:20]}...")

    # Define all tests
    tests = [
        ("API Info Endpoint", test_api_info_endpoint),
        ("Valid Authentication", test_authentication_valid),
        ("Invalid Authentication", test_authentication_invalid),
        ("Missing Authentication", test_authentication_missing),
        ("Models List", test_models_list),
        ("Model Status", test_models_status),
        ("Health Check", test_health_check),
        ("Chat Completion", test_chat_completion),
        ("Streaming Chat", test_chat_completion_streaming),
        ("CORS Headers", test_cors_headers),
        ("Error Handling", test_error_handling),
    ]

    # Run all tests
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except KeyboardInterrupt:
            print("\n\nTests interrupted by user")
            sys.exit(1)
        except Exception as e:
            print_error(f"Test crashed: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:10} {test_name}")

    print(f"\nTotal: {passed}/{len(results)} passed, {failed} failed")

    if failed > 0:
        print("\n❌ Some tests failed!")
        sys.exit(1)
    else:
        print("\n✅ All API tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
