#!/bin/bash
# Run all critical tests for local LLM service
# This ensures everything is working correctly

set -e  # Exit on any error

echo "======================================================================="
echo "RUNNING ALL CRITICAL TESTS"
echo "======================================================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

run_test() {
    local test_name="$1"
    local test_command="$2"

    echo ""
    echo "======================================================================="
    echo "Running: $test_name"
    echo "======================================================================="

    if eval "$test_command"; then
        echo -e "${GREEN}✓ PASS: $test_name${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL: $test_name${NC}"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
        return 1
    fi
}

# Run tests in order of importance
run_test "GPU Exclusive Access" "python3 test_gpu_exclusive.py" || true
run_test "CORS Configuration" "python3 test_cors.py" || true
run_test "Real User Simulation" "python3 test_actual_user.py" || true
run_test "Playwright E2E Tests" "python3 test_e2e_playwright.py" || true
run_test "API Tests" "python3 test_service.py" || true

# Summary
echo ""
echo "======================================================================="
echo "TEST SUMMARY"
echo "======================================================================="
echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}"

if [ ${TESTS_FAILED} -gt 0 ]; then
    echo ""
    echo -e "${RED}Failed tests:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo -e "  ${RED}✗${NC} $test"
    done
    echo ""
    echo -e "${RED}❌ Some tests failed!${NC}"
    exit 1
else
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "The local LLM service is working correctly:"
    echo "  ✓ GPU exclusive access configured"
    echo "  ✓ CORS headers correctly set for browsers"
    echo "  ✓ WebUI accepts and responds to chat messages"
    echo "  ✓ All browser automation tests passing"
    echo "  ✓ API endpoints responding correctly"
    exit 0
fi
