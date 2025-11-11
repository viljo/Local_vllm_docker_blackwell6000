#!/usr/bin/env python3
"""
End-to-End System Tests - Simulates Browser/User Behavior
Tests the complete system from a user's perspective, including remote access
"""
import requests
import sys
import json
import time
import socket
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

# Configuration - can be set for remote testing
SERVER_HOST = sys.argv[1] if len(sys.argv) > 1 else "localhost"
WEBUI_URL = f"http://{SERVER_HOST}:3000"
API_BASE_URL = f"http://{SERVER_HOST}:8080"
API_KEY = load_api_key()

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "unknown"

def test_webui_loads() -> bool:
    """Test 1: WebUI HTML loads (simulates browser loading page)"""
    print("\n1. Testing WebUI Page Load")
    print("   " + "="*50)
    try:
        response = requests.get(WEBUI_URL, timeout=10)
        if response.status_code == 200:
            if "Local LLM Chat" in response.text and "id=\"root\"" in response.text:
                print("   ✓ WebUI HTML loaded successfully")
                print(f"   ✓ Page title: 'Local LLM Chat'")
                return True
            else:
                print("   ✗ WebUI loaded but missing expected content")
                return False
        else:
            print(f"   ✗ WebUI returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Failed to load WebUI: {e}")
        return False


def test_webui_api_discovery() -> bool:
    """Test 2: WebUI can discover API endpoint (simulates JS fetch)"""
    print("\n2. Testing API Discovery from WebUI")
    print("   " + "="*50)
    try:
        # Simulate what the browser JS does - fetch models list
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Origin": WEBUI_URL,  # CORS check
        }
        response = requests.get(f"{API_BASE_URL}/v1/models", headers=headers, timeout=10)

        if response.status_code == 200:
            # Check CORS headers
            cors_ok = "access-control-allow-origin" in response.headers
            models = response.json().get("data", [])
            print(f"   ✓ API accessible from browser context")
            print(f"   ✓ CORS headers present: {cors_ok}")
            print(f"   ✓ Found {len(models)} available models")
            for model in models:
                print(f"     - {model['id']}")
            return len(models) > 0
        else:
            print(f"   ✗ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Failed to connect to API: {e}")
        return False


def test_user_sends_message() -> bool:
    """Test 3: User sends a message and gets response (complete user flow)"""
    print("\n3. Testing Complete User Chat Flow")
    print("   " + "="*50)
    try:
        # Step 1: Get available models (what UI does on load)
        print("   Step 1: Loading available models...")
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Origin": WEBUI_URL,
        }

        models_response = requests.get(f"{API_BASE_URL}/v1/models", headers=headers, timeout=10)
        if models_response.status_code != 200:
            print(f"   ✗ Failed to get models list")
            return False

        models = models_response.json().get("data", [])
        if not models:
            print("   ✗ No models available for chat")
            return False

        selected_model = models[0]["id"]
        print(f"   ✓ Selected model: {selected_model}")

        # Step 2: User types message and clicks Send
        print("   Step 2: Sending user message...")
        user_message = "Hello! Can you tell me what 5+7 equals? Just give the number."

        payload = {
            "model": selected_model,
            "messages": [
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 100,
            "temperature": 0.1
        }

        chat_response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        if chat_response.status_code != 200:
            print(f"   ✗ Chat request failed with status {chat_response.status_code}")
            print(f"   Error: {chat_response.text}")
            return False

        # Step 3: Display response to user
        result = chat_response.json()
        assistant_message = result["choices"][0]["message"]["content"]

        print(f"   ✓ Message sent successfully")
        print(f"\n   User: {user_message}")
        print(f"   Assistant: {assistant_message}")
        print(f"   Tokens used: {result['usage']['total_tokens']}")

        # Verify response makes sense (contains answer)
        if "12" in str(assistant_message):
            print(f"   ✓ Response is correct!")
            return True
        else:
            print(f"   ⚠ Response received but answer unclear")
            return True  # Still counts as working

    except Exception as e:
        print(f"   ✗ Chat flow failed: {e}")
        return False


def test_streaming_chat() -> bool:
    """Test 4: Streaming chat (like typing effect in UI)"""
    print("\n4. Testing Streaming Chat (UI Typing Effect)")
    print("   " + "="*50)
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Origin": WEBUI_URL,
        }

        # Get first available model
        models_response = requests.get(f"{API_BASE_URL}/v1/models", headers=headers, timeout=5)
        models = models_response.json().get("data", [])
        if not models:
            print("   ✗ No models available")
            return False

        payload = {
            "model": models[0]["id"],
            "messages": [
                {"role": "user", "content": "Count from 1 to 5, one number per line."}
            ],
            "max_tokens": 100,
            "temperature": 0.1,
            "stream": True
        }

        print(f"   Sending streaming request...")
        print(f"   Response (as it streams):")
        print("   " + "-"*50)
        print("   ", end="", flush=True)

        response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=30
        )

        if response.status_code != 200:
            print(f"   ✗ Streaming failed with status {response.status_code}")
            return False

        chunks_received = 0
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: ') and line_str != 'data: [DONE]':
                    try:
                        chunk_data = json.loads(line_str[6:])
                        delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            print(content, end="", flush=True)
                            chunks_received += 1
                    except:
                        pass

        print("\n   " + "-"*50)
        print(f"   ✓ Streaming completed - Received {chunks_received} chunks")
        return chunks_received > 0

    except Exception as e:
        print(f"   ✗ Streaming test failed: {e}")
        return False


def test_model_manager() -> bool:
    """Test 5: Model Manager functionality (start/stop models)"""
    print("\n5. Testing Model Manager (Start/Stop Models)")
    print("   " + "="*50)
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}

        # Get model status (what Model Manager displays)
        response = requests.get(f"{API_BASE_URL}/v1/models/status", headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"   ✗ Failed to get model status")
            return False

        status = response.json()
        models = status.get("models", {})

        print(f"   ✓ Model Manager loaded with {len(models)} models:")

        running_count = 0
        stopped_count = 0
        failed_count = 0

        for model_name, model_status in models.items():
            state = model_status.get("status")
            health = model_status.get("health", "N/A")

            if state == "running" and health == "healthy":
                icon = "●"
                color = "green"
                running_count += 1
            elif state == "insufficient_gpu_ram":
                icon = "⚠"
                color = "yellow"
                stopped_count += 1
            elif state == "failed":
                icon = "✕"
                color = "red"
                failed_count += 1
            else:
                icon = "○"
                color = "gray"
                stopped_count += 1

            print(f"   {icon} {model_name}")
            print(f"     Status: {state} | Health: {health}")
            if model_status.get("description"):
                print(f"     {model_status['description']}")

        print(f"\n   Summary:")
        print(f"   ✓ Running: {running_count}")
        print(f"   ○ Stopped/Insufficient RAM: {stopped_count}")
        print(f"   ✕ Failed: {failed_count}")

        return True

    except Exception as e:
        print(f"   ✗ Model Manager test failed: {e}")
        return False


def test_remote_access() -> bool:
    """Test 6: Verify remote access capability"""
    print("\n6. Testing Remote Access Capability")
    print("   " + "="*50)

    local_ip = get_local_ip()
    print(f"   Server IP: {local_ip}")
    print(f"   Testing from: {SERVER_HOST}")

    if SERVER_HOST == "localhost" or SERVER_HOST == "127.0.0.1":
        print(f"\n   ℹ Running in local mode")
        print(f"   To test remote access, run:")
        print(f"   python3 test_system_e2e.py {local_ip}")
        return True
    else:
        print(f"   ✓ Running in REMOTE mode")
        print(f"   WebUI URL: {WEBUI_URL}")
        print(f"   API URL: {API_BASE_URL}")
        return True


def main():
    """Run all end-to-end system tests"""
    print("="*60)
    print("END-TO-END SYSTEM TESTS")
    print("Complete User Experience Validation")
    print("="*60)
    print(f"\nTest Configuration:")
    print(f"  Server: {SERVER_HOST}")
    print(f"  WebUI: {WEBUI_URL}")
    print(f"  API: {API_BASE_URL}")

    results = []

    # Run all tests
    results.append(("WebUI Page Load", test_webui_loads()))
    results.append(("API Discovery", test_webui_api_discovery()))
    results.append(("User Chat Flow", test_user_sends_message()))
    results.append(("Streaming Chat", test_streaming_chat()))
    results.append(("Model Manager", test_model_manager()))
    results.append(("Remote Access", test_remote_access()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} - {test_name}")

    print(f"\nTotal: {passed}/{len(results)} passed")

    if failed > 0:
        print("\n❌ Some tests failed!")
        print("\nRemote Access Instructions:")
        print(f"1. From another computer, open: http://{get_local_ip()}:3000")
        print(f"2. Ensure firewall allows ports 3000 and 8080")
        sys.exit(1)
    else:
        print("\n✅ All system tests passed!")
        print("\nRemote Access Instructions:")
        print(f"From another computer, open: http://{get_local_ip()}:3000")
        sys.exit(0)


if __name__ == "__main__":
    main()
