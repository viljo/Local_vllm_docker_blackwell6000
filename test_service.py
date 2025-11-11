#!/usr/bin/env python3
"""
Test script to verify LLM API and WebUI are working correctly
"""
import requests
import sys
import json
import os
from typing import Dict, Any
from pathlib import Path

# Load API key from .env file
def load_api_key():
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("Error: .env file not found. Please create it from .env.example")
        sys.exit(1)

    with open(env_file) as f:
        for line in f:
            if line.startswith("API_KEY="):
                return line.strip().split("=", 1)[1]

    print("Error: API_KEY not found in .env file")
    sys.exit(1)

# Configuration
API_BASE_URL = "http://localhost:8080"
WEBUI_URL = "http://localhost:3000"
API_KEY = load_api_key()

def test_api_health() -> bool:
    """Test if the API health endpoint responds"""
    print("Testing API health endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✓ API health check passed")
            return True
        else:
            print(f"✗ API health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ API health check failed: {e}")
        return False


def test_models_list() -> bool:
    """Test if the models list endpoint works"""
    print("\nTesting models list endpoint...")
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = requests.get(f"{API_BASE_URL}/v1/models", headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            print(f"✓ Models list endpoint working - Found {len(models)} models")
            for model in models:
                print(f"  - {model.get('id')}: {model.get('status', 'unknown')}")
            return True
        else:
            print(f"✗ Models list failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Models list failed: {e}")
        return False


def test_models_status() -> Dict[str, Any]:
    """Test if the models status endpoint works and return model statuses"""
    print("\nTesting models status endpoint...")
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        response = requests.get(f"{API_BASE_URL}/v1/models/status", headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", {})
            print(f"✓ Models status endpoint working")

            # Find a running model
            running_models = {}
            for name, status in models.items():
                state = status.get("status")
                health = status.get("health", "N/A")
                print(f"  - {name}: {state} (health: {health})")
                if state == "running" and health == "healthy":
                    running_models[name] = status

            return running_models
        else:
            print(f"✗ Models status failed with status {response.status_code}")
            return {}
    except Exception as e:
        print(f"✗ Models status failed: {e}")
        return {}


def test_chat_completion(model_name: str) -> bool:
    """Test if chat completion works for a specific model"""
    print(f"\nTesting chat completion with {model_name}...")
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "Say 'Hello from the LLM!' and nothing else."}
            ],
            "max_tokens": 20,
            "temperature": 0.7
        }

        response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✓ Chat completion successful")
            print(f"  Response: {content}")
            return True
        else:
            print(f"✗ Chat completion failed with status {response.status_code}")
            print(f"  Error: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Chat completion failed: {e}")
        return False


def test_streaming_chat(model_name: str) -> bool:
    """Test if streaming chat completion works"""
    print(f"\nTesting streaming chat completion with {model_name}...")
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "Count from 1 to 3, one number per line."}
            ],
            "max_tokens": 50,
            "temperature": 0.7,
            "stream": True
        }

        response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=30
        )

        if response.status_code == 200:
            chunks_received = 0
            print(f"✓ Streaming started, receiving chunks...")

            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: ') and line_str != 'data: [DONE]':
                        chunks_received += 1
                        if chunks_received <= 3:  # Show first 3 chunks
                            try:
                                chunk_data = json.loads(line_str[6:])
                                delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    print(f"  Chunk {chunks_received}: {repr(content)}")
                            except:
                                pass

            print(f"✓ Streaming completed - Received {chunks_received} chunks")
            return chunks_received > 0
        else:
            print(f"✗ Streaming chat failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Streaming chat failed: {e}")
        return False


def test_only_running_models_selectable() -> bool:
    """Test that only running/healthy models are available in the dropdown"""
    print("\nTesting that only running models are selectable...")
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}

        # Get the list of selectable models from /v1/models (used by dropdown)
        models_response = requests.get(f"{API_BASE_URL}/v1/models", headers=headers, timeout=5)
        if models_response.status_code != 200:
            print(f"✗ Failed to get models list: {models_response.status_code}")
            return False

        selectable_models = {m["id"] for m in models_response.json().get("data", [])}

        # Get the full status of all models
        status_response = requests.get(f"{API_BASE_URL}/v1/models/status", headers=headers, timeout=5)
        if status_response.status_code != 200:
            print(f"✗ Failed to get models status: {status_response.status_code}")
            return False

        all_models = status_response.json().get("models", {})

        # Verify all selectable models are running and healthy
        for model_id in selectable_models:
            if model_id not in all_models:
                print(f"✗ Selectable model '{model_id}' not found in status")
                return False

            status = all_models[model_id]
            if status.get("status") != "running":
                print(f"✗ Selectable model '{model_id}' is not running (status: {status.get('status')})")
                return False

            if status.get("health") != "healthy":
                print(f"✗ Selectable model '{model_id}' is not healthy (health: {status.get('health')})")
                return False

        # Verify non-running/unhealthy models are NOT selectable
        non_running = []
        for model_id, status in all_models.items():
            if status.get("status") != "running" or status.get("health") != "healthy":
                if model_id in selectable_models:
                    print(f"✗ Non-running model '{model_id}' is incorrectly selectable")
                    return False
                non_running.append(model_id)

        print(f"✓ Only running/healthy models are selectable")
        print(f"  Selectable models: {list(selectable_models) if selectable_models else 'none'}")
        print(f"  Non-selectable models: {non_running if non_running else 'none'}")
        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_webui() -> bool:
    """Test if the WebUI is accessible"""
    print("\nTesting WebUI accessibility...")
    try:
        response = requests.get(WEBUI_URL, timeout=5)
        if response.status_code == 200:
            # Check if it's HTML
            if "<!DOCTYPE html>" in response.text or "<html" in response.text:
                print("✓ WebUI is accessible and serving HTML")
                return True
            else:
                print("✗ WebUI responded but not serving HTML")
                return False
        else:
            print(f"✗ WebUI returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ WebUI test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("LLM Service Test Suite")
    print("=" * 60)

    results = []

    # Test API health
    results.append(("API Health", test_api_health()))

    # Test models list
    results.append(("Models List", test_models_list()))

    # Test models status and get running models
    running_models = test_models_status()
    results.append(("Models Status", len(running_models) > 0))

    # Test that only running models are selectable
    results.append(("Only Running Models Selectable", test_only_running_models_selectable()))

    # Test chat completion with first available running model
    if running_models:
        model_name = list(running_models.keys())[0]
        results.append(("Chat Completion", test_chat_completion(model_name)))
        results.append(("Streaming Chat", test_streaming_chat(model_name)))
    else:
        print("\n⚠ No running models found - skipping chat tests")
        results.append(("Chat Completion", None))
        results.append(("Streaming Chat", None))

    # Test WebUI
    results.append(("WebUI", test_webui()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)

    for test_name, result in results:
        if result is True:
            print(f"✓ {test_name}: PASSED")
        elif result is False:
            print(f"✗ {test_name}: FAILED")
        else:
            print(f"⊘ {test_name}: SKIPPED")

    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")

    if failed > 0:
        print("\n❌ Some tests failed!")
        sys.exit(1)
    elif passed == 0:
        print("\n⚠ No tests passed!")
        sys.exit(1)
    else:
        print("\n✅ All active tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
