#!/bin/bash
#==============================================================================
# Installation Test Script
#==============================================================================
# This script tests if the installation was successful
#
# Usage:
#   ./test_installation.sh
#==============================================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

INSTALL_DIR="/opt/local_llm_service"
SERVICE_NAME="local-llm-service"
FAILED=0

echo "========================================================================"
echo "Installation Test Suite"
echo "========================================================================"
echo ""

# Test 1: Check installation directory
print_test "Checking installation directory..."
if [[ -d "$INSTALL_DIR" ]]; then
    print_pass "Installation directory exists: $INSTALL_DIR"
else
    print_fail "Installation directory not found: $INSTALL_DIR"
    ((FAILED++))
fi

# Test 2: Check docker-compose.yml
print_test "Checking docker-compose.yml..."
if [[ -f "$INSTALL_DIR/docker-compose.yml" ]]; then
    print_pass "docker-compose.yml found"
else
    print_fail "docker-compose.yml not found"
    ((FAILED++))
fi

# Test 3: Check systemd service
print_test "Checking systemd service..."
if [[ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]]; then
    print_pass "Systemd service file exists"
else
    print_fail "Systemd service file not found"
    ((FAILED++))
fi

# Test 4: Check service enabled
print_test "Checking if service is enabled..."
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    print_pass "Service is enabled for autostart"
else
    print_fail "Service is not enabled"
    ((FAILED++))
fi

# Test 5: Check service running
print_test "Checking if service is running..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    print_pass "Service is active"
else
    print_fail "Service is not running"
    ((FAILED++))
fi

# Test 6: Check Docker containers
print_test "Checking Docker containers..."
cd "$INSTALL_DIR" 2>/dev/null
CONTAINER_COUNT=$(docker compose ps --status running 2>/dev/null | grep -c "Up" || echo "0")
if [[ $CONTAINER_COUNT -ge 2 ]]; then
    print_pass "Docker containers are running ($CONTAINER_COUNT containers)"
else
    print_fail "Not enough containers running (found $CONTAINER_COUNT, expected 2+)"
    ((FAILED++))
fi

# Test 7: Check WebUI accessibility
print_test "Checking WebUI accessibility..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200"; then
    print_pass "WebUI is accessible at http://localhost:3000"
else
    print_fail "WebUI is not accessible"
    ((FAILED++))
fi

# Test 8: Check API accessibility
print_test "Checking API accessibility..."
if curl -s http://localhost:8080/health | grep -q "status"; then
    print_pass "API is accessible at http://localhost:8080"
else
    print_fail "API is not accessible"
    ((FAILED++))
fi

# Test 9: Check GPU access
print_test "Checking GPU access in containers..."
GPU_CONTAINERS=$(docker ps --filter "name=vllm-" --format "{{.Names}}" 2>/dev/null)
if [[ -n "$GPU_CONTAINERS" ]]; then
    FIRST_CONTAINER=$(echo "$GPU_CONTAINERS" | head -1)
    if docker exec "$FIRST_CONTAINER" nvidia-smi &>/dev/null; then
        print_pass "GPU is accessible in containers"
    else
        print_fail "GPU is not accessible in containers"
        ((FAILED++))
    fi
else
    print_fail "No vLLM containers running"
    ((FAILED++))
fi

# Test 10: Check autostart after boot (simulate)
print_test "Checking autostart configuration..."
SERVICE_WANTED=$(systemctl show -p WantedBy "$SERVICE_NAME" 2>/dev/null | grep "multi-user.target")
if [[ -n "$SERVICE_WANTED" ]]; then
    print_pass "Service is configured to start after boot"
else
    print_fail "Service autostart configuration missing"
    ((FAILED++))
fi

echo ""
echo "========================================================================"
if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo "Installation is working correctly."
else
    echo -e "${RED}❌ $FAILED test(s) failed${NC}"
    echo "Installation may have issues."
fi
echo "========================================================================"
echo ""

if [[ $FAILED -gt 0 ]]; then
    echo "Debugging commands:"
    echo "  - Check service status: sudo systemctl status $SERVICE_NAME"
    echo "  - View service logs: sudo journalctl -u $SERVICE_NAME -n 50"
    echo "  - Check containers: cd $INSTALL_DIR && docker compose ps"
    echo "  - View container logs: cd $INSTALL_DIR && docker compose logs"
    echo ""
fi

exit $FAILED
