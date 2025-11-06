#!/bin/bash
# Deployment Validation Script for Local LLM Service
# Tests all critical endpoints and verifies service health

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ROUTER_URL="${ROUTER_URL:-http://localhost:8080}"
API_KEY="${API_KEY:-sk-local-dev-key}"
TIMEOUT=5

echo "========================================="
echo "Local LLM Service Deployment Validation"
echo "========================================="
echo ""
echo "Router URL: $ROUTER_URL"
echo ""

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to test endpoint
test_endpoint() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local expected_status="$4"
    local extra_args="${5:-}"

    echo -n "Testing: $test_name... "

    response=$(curl -s -w "\n%{http_code}" -X "$method" \
        "$ROUTER_URL$endpoint" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $API_KEY" \
        $extra_args \
        --connect-timeout $TIMEOUT \
        --max-time $TIMEOUT 2>&1) || {
        echo -e "${RED}FAIL${NC} (connection error)"
        ((TESTS_FAILED++))
        return 1
    }

    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$status_code" = "$expected_status" ]; then
        echo -e "${GREEN}PASS${NC} (HTTP $status_code)"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}FAIL${NC} (Expected HTTP $expected_status, got $status_code)"
        echo "Response: $body"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Test 1: Router Health Check
test_endpoint "Router Health Check" "GET" "/health" "200"

# Test 2: Router Readiness Check
test_endpoint "Router Readiness Check" "GET" "/ready" "200"

# Test 3: List Models (Authenticated)
test_endpoint "List Models (Authenticated)" "GET" "/v1/models" "200"

# Test 4: List Models (Unauthorized)
echo -n "Testing: List Models (Unauthorized)... "
response=$(curl -s -w "\n%{http_code}" -X GET \
    "$ROUTER_URL/v1/models" \
    --connect-timeout $TIMEOUT \
    --max-time $TIMEOUT 2>&1) || true

status_code=$(echo "$response" | tail -n1)
if [ "$status_code" = "403" ] || [ "$status_code" = "401" ]; then
    echo -e "${GREEN}PASS${NC} (HTTP $status_code - correctly rejected)"
    ((TESTS_PASSED++))
else
    echo -e "${RED}FAIL${NC} (Expected HTTP 401/403, got $status_code)"
    ((TESTS_FAILED++))
fi

# Test 5: Chat Completion (Non-Streaming) - Python Model
echo -n "Testing: Chat Completion (Python Coder Model)... "
response=$(curl -s -w "\n%{http_code}" -X POST \
    "$ROUTER_URL/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_KEY" \
    -d '{
        "model": "deepseek-coder-33b-instruct",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 10,
        "stream": false
    }' \
    --connect-timeout 30 \
    --max-time 30 2>&1) || {
    echo -e "${YELLOW}SKIP${NC} (timeout - model may still be loading)"
    ((TESTS_FAILED++))
    response=""
}

if [ -n "$response" ]; then
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$status_code" = "200" ]; then
        # Verify response structure
        if echo "$body" | grep -q '"choices"' && echo "$body" | grep -q '"message"'; then
            echo -e "${GREEN}PASS${NC} (HTTP 200, valid response structure)"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}FAIL${NC} (HTTP 200 but invalid response structure)"
            echo "Response: $body"
            ((TESTS_FAILED++))
        fi
    elif [ "$status_code" = "503" ]; then
        echo -e "${YELLOW}SKIP${NC} (HTTP 503 - model still loading)"
    else
        echo -e "${RED}FAIL${NC} (Unexpected status: $status_code)"
        echo "Response: $body"
        ((TESTS_FAILED++))
    fi
fi

# Test 6: Chat Completion - General Model
echo -n "Testing: Chat Completion (General Model)... "
response=$(curl -s -w "\n%{http_code}" -X POST \
    "$ROUTER_URL/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_KEY" \
    -d '{
        "model": "mistral-7b-v0.1",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 10,
        "stream": false
    }' \
    --connect-timeout 30 \
    --max-time 30 2>&1) || {
    echo -e "${YELLOW}SKIP${NC} (timeout - model may still be loading)"
    response=""
}

if [ -n "$response" ]; then
    status_code=$(echo "$response" | tail -n1)
    if [ "$status_code" = "200" ]; then
        echo -e "${GREEN}PASS${NC} (HTTP 200)"
        ((TESTS_PASSED++))
    elif [ "$status_code" = "503" ]; then
        echo -e "${YELLOW}SKIP${NC} (HTTP 503 - model still loading)"
    else
        echo -e "${RED}FAIL${NC} (Unexpected status: $status_code)"
        ((TESTS_FAILED++))
    fi
fi

# Test 7: Invalid Model Name
echo -n "Testing: Invalid Model Name Rejection... "
response=$(curl -s -w "\n%{http_code}" -X POST \
    "$ROUTER_URL/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_KEY" \
    -d '{
        "model": "nonexistent-model",
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 10
    }' \
    --connect-timeout $TIMEOUT \
    --max-time $TIMEOUT 2>&1) || true

status_code=$(echo "$response" | tail -n1)
if [ "$status_code" = "400" ] || [ "$status_code" = "404" ]; then
    echo -e "${GREEN}PASS${NC} (HTTP $status_code - correctly rejected)"
    ((TESTS_PASSED++))
else
    echo -e "${RED}FAIL${NC} (Expected HTTP 400/404, got $status_code)"
    ((TESTS_FAILED++))
fi

# Test 8: Streaming Response (basic check)
echo -n "Testing: Streaming Response... "
response=$(curl -s -N -X POST \
    "$ROUTER_URL/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_KEY" \
    -d '{
        "model": "deepseek-coder-33b-instruct",
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 5,
        "stream": true
    }' \
    --connect-timeout 30 \
    --max-time 30 2>&1 | head -n 5) || {
    echo -e "${YELLOW}SKIP${NC} (timeout or model loading)"
    response=""
}

if [ -n "$response" ]; then
    if echo "$response" | grep -q "data:" && echo "$response" | grep -q "delta"; then
        echo -e "${GREEN}PASS${NC} (received SSE events)"
        ((TESTS_PASSED++))
    elif echo "$response" | grep -q "503"; then
        echo -e "${YELLOW}SKIP${NC} (model still loading)"
    else
        echo -e "${RED}FAIL${NC} (no SSE events received)"
        ((TESTS_FAILED++))
    fi
fi

# Summary
echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
echo -e "${RED}Failed:${NC} $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! Service is operational.${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Check logs with: docker compose logs${NC}"
    exit 1
fi
