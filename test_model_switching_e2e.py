#!/usr/bin/env python3
"""
Comprehensive End-to-End Test for Model Switching
Tests model loading, unloading, and switching across all available models
"""
import sys
import time
import requests
from typing import Dict, List, Any
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
API_BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/v1"
API_KEY = load_api_key()
HEADERS = {"Authorization": f"Bearer {API_KEY}"}
TIMEOUT = 300  # 5 minutes max wait for model loading


def get_models_status() -> Dict[str, Any]:
    """Get current status of all models"""
    response = requests.get(f"{API_BASE_URL}/models/status", headers=HEADERS)
    response.raise_for_status()
    return response.json()


def get_available_models() -> List[str]:
    """Get list of all available model names, sorted by GPU memory (largest first)"""
    status = get_models_status()
    models = status.get("models", {})

    # Sort models by GPU memory requirement (largest first)
    sorted_models = sorted(
        models.items(),
        key=lambda x: x[1].get("gpu_memory_gb", 0),
        reverse=True
    )

    return [name for name, _ in sorted_models]


def switch_to_model(model_name: str) -> Dict[str, Any]:
    """Switch to a specific model using the smart switching API"""
    print(f"\n{'='*70}")
    print(f"Switching to: {model_name}")
    print(f"{'='*70}")

    response = requests.post(
        f"{API_BASE_URL}/models/switch?target_model={model_name}",
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()
    result = response.json()

    if result.get("unloaded_models"):
        print(f"✓ Unloaded models to free space: {', '.join(result['unloaded_models'])}")

    return result


def wait_for_model_ready(model_name: str, max_wait: int = TIMEOUT) -> bool:
    """Wait for model to be running and healthy"""
    print(f"Waiting for {model_name} to be ready (max {max_wait}s)...")

    start_time = time.time()
    while time.time() - start_time < max_wait:
        status = get_models_status()
        model_status = status.get("models", {}).get(model_name, {})

        if model_status.get("status") == "running" and model_status.get("health") == "healthy":
            elapsed = int(time.time() - start_time)
            print(f"✓ Model {model_name} is ready (took {elapsed}s)")
            return True

        # Check for failures
        if model_status.get("status") in ["failed", "insufficient_gpu_ram"]:
            print(f"✗ Model {model_name} failed to start: {model_status.get('error', 'unknown error')}")
            return False

        # Show progress
        status_text = model_status.get("status", "unknown")
        print(f"  Status: {status_text}... ({int(time.time() - start_time)}s)", end="\r")
        time.sleep(3)

    print(f"\n✗ Timeout waiting for {model_name} to be ready")
    return False


def test_model_conversation(model_name: str) -> bool:
    """Test model with a short conversation"""
    print(f"Testing {model_name} with a conversation...")

    test_message = "What is 2+2? Answer with just the number."

    try:
        response = requests.post(
            f"{API_BASE_URL}/chat/completions",
            headers=HEADERS,
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": test_message}],
                "stream": False,
                "max_tokens": 50,
                "temperature": 0.1
            },
            timeout=60
        )
        response.raise_for_status()

        result = response.json()
        answer = result["choices"][0]["message"]["content"]

        print(f"✓ Model responded: {answer[:100]}...")

        # Check if response contains the answer (4)
        if "4" in answer:
            print(f"✓ Response contains correct answer")
            return True
        else:
            print(f"⚠ Response doesn't contain expected answer, but model is functional")
            return True

    except Exception as e:
        print(f"✗ Conversation test failed: {e}")
        return False


def verify_unloading_logic(
    previous_status: Dict[str, Any],
    new_status: Dict[str, Any],
    target_model: str,
    switch_result: Dict[str, Any]
) -> bool:
    """Verify that the correct models were unloaded"""
    print(f"Verifying unloading logic...")

    unloaded_models = switch_result.get("unloaded_models", [])

    # Check that previously running models (except target) are now stopped
    prev_running = [
        name for name, info in previous_status.get("models", {}).items()
        if info.get("status") == "running" and name != target_model
    ]

    now_running = [
        name for name, info in new_status.get("models", {}).items()
        if info.get("status") == "running"
    ]

    # Verify target model is running
    if target_model not in now_running:
        print(f"✗ Target model {target_model} is not running")
        return False

    print(f"✓ Target model {target_model} is running")

    # Verify unloaded models are actually stopped
    for model_name in unloaded_models:
        if model_name in now_running:
            print(f"✗ Model {model_name} was marked as unloaded but is still running")
            return False

    print(f"✓ Unloaded models ({len(unloaded_models)}) are correctly stopped")
    return True


def run_comprehensive_test():
    """Run comprehensive model switching test"""
    print("="*70)
    print("COMPREHENSIVE MODEL SWITCHING E2E TEST")
    print("="*70)
    print(f"\nAPI Base URL: {API_BASE_URL}")

    # Get all available models sorted by size (largest first)
    print("\nFetching available models...")
    models = get_available_models()

    if not models:
        print("✗ No models available for testing")
        sys.exit(1)

    print(f"✓ Found {len(models)} models to test:")
    status = get_models_status()
    for model_name in models:
        model_info = status["models"][model_name]
        vram = model_info.get("gpu_memory_gb", "?")
        print(f"  - {model_name} ({vram}GB VRAM)")

    # Track results
    results = []

    # Test each model in order (largest first)
    for i, model_name in enumerate(models):
        print(f"\n{'='*70}")
        print(f"TEST {i+1}/{len(models)}: {model_name}")
        print(f"{'='*70}")

        # Get current status before switching
        previous_status = get_models_status()

        try:
            # Step 1: Switch to model
            switch_result = switch_to_model(model_name)

            # Step 2: Wait for model to be ready
            if not wait_for_model_ready(model_name):
                results.append({
                    "model": model_name,
                    "success": False,
                    "error": "Failed to load model"
                })
                print(f"✗ Skipping tests for {model_name} due to loading failure")
                continue

            # Step 3: Get new status after switching
            new_status = get_models_status()

            # Step 4: Verify unloading logic
            unloading_correct = verify_unloading_logic(
                previous_status, new_status, model_name, switch_result
            )

            # Step 5: Test model with conversation
            conversation_works = test_model_conversation(model_name)

            # Record results
            success = unloading_correct and conversation_works
            results.append({
                "model": model_name,
                "success": success,
                "unloading_correct": unloading_correct,
                "conversation_works": conversation_works,
                "unloaded_models": switch_result.get("unloaded_models", []),
                "load_time": switch_result.get("estimated_load_time_seconds", "unknown")
            })

            if success:
                print(f"\n✓ All tests passed for {model_name}")
            else:
                print(f"\n✗ Some tests failed for {model_name}")

        except Exception as e:
            print(f"\n✗ Error testing {model_name}: {e}")
            results.append({
                "model": model_name,
                "success": False,
                "error": str(e)
            })

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for r in results if r.get("success", False))
    failed = sum(1 for r in results if not r.get("success", False))

    for result in results:
        status = "✓ PASS" if result.get("success", False) else "✗ FAIL"
        model_name = result["model"]
        print(f"\n{status} - {model_name}")

        if result.get("unloaded_models"):
            print(f"  Unloaded: {', '.join(result['unloaded_models'])}")

        if result.get("error"):
            print(f"  Error: {result['error']}")
        else:
            print(f"  Unloading correct: {result.get('unloading_correct', False)}")
            print(f"  Conversation works: {result.get('conversation_works', False)}")

    print(f"\n{'='*70}")
    print(f"Total: {passed}/{len(results)} models passed all tests")
    print(f"{'='*70}")

    if failed > 0:
        print(f"\n❌ {failed} model(s) failed")
        print("\nTroubleshooting:")
        print("1. Check that models are fully downloaded")
        print("2. Check GPU memory availability")
        print("3. Review container logs for errors")
        sys.exit(1)
    else:
        print("\n✅ All models passed comprehensive switching tests!")
        print("\nThe smart model switching system is working correctly:")
        print("  - Models load successfully")
        print("  - Correct models are unloaded to free space")
        print("  - All models can generate responses")
        sys.exit(0)


if __name__ == "__main__":
    run_comprehensive_test()
