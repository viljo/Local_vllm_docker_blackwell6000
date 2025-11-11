#!/usr/bin/env python3
"""
CORS Configuration Tests
Prevents regression of CORS headers, especially Authorization header
"""
import requests
import sys

API_BASE_URL = "http://localhost:8080"
WEBUI_ORIGIN = "http://172.30.0.54:3000"

def test_cors_preflight_models():
    """Test CORS preflight for /v1/models endpoint"""
    print("\n" + "="*70)
    print("Test 1: CORS Preflight - /v1/models")
    print("="*70)

    response = requests.options(
        f"{API_BASE_URL}/v1/models",
        headers={
            "Origin": WEBUI_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization"
        }
    )

    print(f"Status code: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Check CORS headers
    headers = response.headers

    # 1. Check Access-Control-Allow-Origin
    assert "Access-Control-Allow-Origin" in headers, "Missing Access-Control-Allow-Origin"
    print(f"✓ Access-Control-Allow-Origin: {headers['Access-Control-Allow-Origin']}")

    # 2. Check Access-Control-Allow-Methods
    assert "Access-Control-Allow-Methods" in headers, "Missing Access-Control-Allow-Methods"
    print(f"✓ Access-Control-Allow-Methods: {headers['Access-Control-Allow-Methods']}")

    # 3. CRITICAL: Check that Authorization is explicitly listed
    assert "Access-Control-Allow-Headers" in headers, "Missing Access-Control-Allow-Headers"
    allowed_headers = headers["Access-Control-Allow-Headers"]
    print(f"✓ Access-Control-Allow-Headers: {allowed_headers}")

    # This is the critical check to prevent regression
    if allowed_headers == "*":
        print("✗ FAIL: Access-Control-Allow-Headers is '*' (wildcard)")
        print("✗ The Authorization header MUST be explicitly listed!")
        print("✗ Wildcard '*' does NOT cover the Authorization header per CORS spec")
        return False

    if "Authorization" not in allowed_headers:
        print("✗ FAIL: 'Authorization' not found in Access-Control-Allow-Headers")
        print(f"✗ Current value: {allowed_headers}")
        return False

    print("✓ Authorization header is explicitly listed (CORRECT)")
    print("✓ PASS: CORS preflight headers are correct")
    return True


def test_cors_preflight_models_status():
    """Test CORS preflight for /v1/models/status endpoint"""
    print("\n" + "="*70)
    print("Test 2: CORS Preflight - /v1/models/status")
    print("="*70)

    response = requests.options(
        f"{API_BASE_URL}/v1/models/status",
        headers={
            "Origin": WEBUI_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization"
        }
    )

    print(f"Status code: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    headers = response.headers
    allowed_headers = headers.get("Access-Control-Allow-Headers", "")

    print(f"Access-Control-Allow-Headers: {allowed_headers}")

    if allowed_headers == "*":
        print("✗ FAIL: Using wildcard '*' instead of explicit header list")
        return False

    if "Authorization" not in allowed_headers:
        print("✗ FAIL: Authorization not explicitly listed")
        return False

    print("✓ PASS: Authorization header explicitly listed")
    return True


def test_cors_preflight_chat():
    """Test CORS preflight for /v1/chat/completions endpoint"""
    print("\n" + "="*70)
    print("Test 3: CORS Preflight - /v1/chat/completions")
    print("="*70)

    response = requests.options(
        f"{API_BASE_URL}/v1/chat/completions",
        headers={
            "Origin": WEBUI_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type"
        }
    )

    print(f"Status code: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    headers = response.headers
    allowed_headers = headers.get("Access-Control-Allow-Headers", "")

    print(f"Access-Control-Allow-Headers: {allowed_headers}")

    if allowed_headers == "*":
        print("✗ FAIL: Using wildcard '*' instead of explicit header list")
        return False

    required_headers = ["Authorization", "Content-Type"]
    for header in required_headers:
        if header not in allowed_headers:
            print(f"✗ FAIL: '{header}' not explicitly listed")
            return False
        print(f"✓ {header} found")

    print("✓ PASS: All required headers explicitly listed")
    return True


def test_actual_api_call_with_auth():
    """Test that actual API calls work with Authorization header"""
    print("\n" + "="*70)
    print("Test 4: Actual API Call with Authorization Header")
    print("="*70)

    # Test /v1/models endpoint
    response = requests.get(
        f"{API_BASE_URL}/v1/models",
        headers={
            "Authorization": "Bearer sk-local-2ac9387d659f7131f38d83e5f7bee469",
            "Origin": WEBUI_ORIGIN
        }
    )

    print(f"GET /v1/models status: {response.status_code}")

    if response.status_code != 200:
        print("✗ FAIL: API call failed")
        print(f"Response: {response.text[:200]}")
        return False

    # Check CORS headers on actual response (not preflight)
    headers = response.headers
    assert "Access-Control-Allow-Origin" in headers, "Missing CORS header on actual response"

    print(f"✓ API call successful")
    print(f"✓ Access-Control-Allow-Origin: {headers['Access-Control-Allow-Origin']}")
    print("✓ PASS: API accepts Authorization header")
    return True


def test_cors_headers_summary():
    """Print a summary of all CORS headers for documentation"""
    print("\n" + "="*70)
    print("Test 5: CORS Headers Summary")
    print("="*70)

    response = requests.options(
        f"{API_BASE_URL}/v1/models",
        headers={
            "Origin": WEBUI_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization"
        }
    )

    cors_headers = {
        k: v for k, v in response.headers.items()
        if k.lower().startswith("access-control")
    }

    print("\nAll CORS headers:")
    for header, value in sorted(cors_headers.items()):
        print(f"  {header}: {value}")

    print("\n✓ PASS: Summary complete")
    return True


def run_all_tests():
    """Run all CORS tests"""
    print("="*70)
    print("CORS CONFIGURATION TESTS")
    print("Prevents regression of CORS headers (especially Authorization)")
    print("="*70)

    results = []

    try:
        results.append(("CORS Preflight /v1/models", test_cors_preflight_models()))
        results.append(("CORS Preflight /v1/models/status", test_cors_preflight_models_status()))
        results.append(("CORS Preflight /v1/chat/completions", test_cors_preflight_chat()))
        results.append(("Actual API Call with Auth", test_actual_api_call_with_auth()))
        results.append(("CORS Headers Summary", test_cors_headers_summary()))
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    failed = sum(1 for _, result in results if not result)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} - {test_name}")

    print(f"\nTotal: {passed}/{len(results)} passed")

    if failed > 0:
        print("\n❌ CORS tests failed!")
        print("\nCritical Issue:")
        print("  The Authorization header must be EXPLICITLY listed in Access-Control-Allow-Headers")
        print("  Using wildcard '*' does NOT cover the Authorization header per CORS spec")
        print("\nTo fix:")
        print("  Edit router/app/main.py:")
        print("  - Line 95: allow_headers=[\"Content-Type\", \"Authorization\", \"Accept\", \"Origin\", \"X-Requested-With\"]")
        print("  - Line 106: response.headers[\"Access-Control-Allow-Headers\"] = \"Content-Type, Authorization, ...\"")
        print("\nThen rebuild:")
        print("  docker compose build vllm-router && docker compose up -d vllm-router")
        return False
    else:
        print("\n✅ All CORS tests passed!")
        print("\nThe Authorization header is correctly configured:")
        print("  ✓ Explicitly listed in Access-Control-Allow-Headers")
        print("  ✓ NOT using wildcard '*' (which would break in browsers)")
        print("  ✓ API calls with Authorization header work correctly")
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
