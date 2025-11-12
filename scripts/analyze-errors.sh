#!/bin/bash

# Error Analysis Script
# Analyzes router logs to identify common errors and issues

echo "================================================================================"
echo "API ERROR ANALYSIS"
echo "================================================================================"
echo ""

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get time range (default: last hour)
TIME_RANGE="${1:-1h}"

echo -e "${CYAN}Analyzing logs from last: $TIME_RANGE${NC}"
echo ""

# Get logs
LOGS=$(docker logs vllm-router --since "$TIME_RANGE" 2>&1)

# Count errors by type
echo "=== ERROR SUMMARY ==="
echo ""

ERROR_COUNT=$(echo "$LOGS" | grep -c "ERROR" 2>/dev/null)
WARNING_COUNT=$(echo "$LOGS" | grep -c "WARNING" 2>/dev/null)
AUTH_FAIL_COUNT=$(echo "$LOGS" | grep -c "Invalid API key" 2>/dev/null)
BACKEND_ERROR_COUNT=$(echo "$LOGS" | grep -c "Backend error" 2>/dev/null)
TIMEOUT_COUNT=$(echo "$LOGS" | grep -c "TimeoutException" 2>/dev/null)
CONNECT_ERROR_COUNT=$(echo "$LOGS" | grep -c "ConnectError" 2>/dev/null)

echo -e "Total Errors:           ${RED}$ERROR_COUNT${NC}"
echo -e "Total Warnings:         ${YELLOW}$WARNING_COUNT${NC}"
echo -e "Auth Failures:          $AUTH_FAIL_COUNT"
echo -e "Backend Errors:         $BACKEND_ERROR_COUNT"
echo -e "Timeouts:               $TIMEOUT_COUNT"
echo -e "Connection Errors:      $CONNECT_ERROR_COUNT"
echo ""

# Status code summary
echo "=== HTTP STATUS CODES ==="
echo ""
echo "$LOGS" | grep -oE "HTTP/[0-9.]+ [0-9]{3}" | sort | uniq -c | sort -rn || echo "No HTTP status codes found"
echo ""

# Top error messages
echo "=== TOP ERROR MESSAGES ==="
echo ""
echo "$LOGS" | grep "ERROR" | sed -E 's/.*ERROR - //' | sort | uniq -c | sort -rn | head -10 || echo "No errors found"
echo ""

# Authentication failures by IP
if [ "$AUTH_FAIL_COUNT" -gt 0 ]; then
    echo "=== AUTHENTICATION FAILURES BY IP ==="
    echo ""
    echo "$LOGS" | grep "Invalid API key" | grep -oE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" | sort | uniq -c | sort -rn || echo "No IPs found"
    echo ""
fi

# Backend errors
if [ "$BACKEND_ERROR_COUNT" -gt 0 ]; then
    echo "=== RECENT BACKEND ERRORS ==="
    echo ""
    echo "$LOGS" | grep "Backend error" | tail -5
    echo ""
fi

# Timeouts
if [ "$TIMEOUT_COUNT" -gt 0 ]; then
    echo "=== TIMEOUT EVENTS ==="
    echo ""
    echo "$LOGS" | grep -E "TimeoutException|timeout" | tail -5
    echo ""
fi

# Failed requests by endpoint
echo "=== REQUESTS BY ENDPOINT ==="
echo ""
echo "$LOGS" | grep -oE '"(GET|POST|PUT|DELETE) /[^"]*"' | sort | uniq -c | sort -rn | head -10 || echo "No endpoints found"
echo ""

# Tool calling errors
TOOL_ERROR_COUNT=$(echo "$LOGS" | grep -c "Tool validation error" 2>/dev/null)
if [ "$TOOL_ERROR_COUNT" -gt 0 ]; then
    echo "=== TOOL CALLING ERRORS ==="
    echo ""
    echo "$LOGS" | grep "Tool validation error" | tail -5
    echo ""
fi

# Recent critical errors with context
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "=== LAST 3 ERROR EVENTS (with context) ==="
    echo ""

    # Get line numbers of errors
    ERROR_LINES=$(echo "$LOGS" | grep -n "ERROR" | tail -3 | cut -d: -f1)

    for line in $ERROR_LINES; do
        echo "--- Error at line $line ---"
        # Show 2 lines before and 5 lines after each error
        echo "$LOGS" | sed -n "$((line-2)),$((line+5))p"
        echo ""
    done
fi

# Recommendations
echo "================================================================================"
echo "RECOMMENDATIONS"
echo "================================================================================"
echo ""

if [ "$AUTH_FAIL_COUNT" -gt 10 ]; then
    echo -e "${YELLOW}⚠ High number of authentication failures detected${NC}"
    echo "  Consider checking API key configuration on remote clients"
    echo ""
fi

if [ "$BACKEND_ERROR_COUNT" -gt 5 ]; then
    echo -e "${YELLOW}⚠ Backend errors detected${NC}"
    echo "  Check backend model services: docker ps | grep vllm"
    echo ""
fi

if [ "$TIMEOUT_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠ Timeout events detected${NC}"
    echo "  Consider increasing timeout values or checking model response times"
    echo ""
fi

if [ "$ERROR_COUNT" -eq 0 ] && [ "$WARNING_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ No errors or warnings found in the specified time range${NC}"
    echo ""
fi

echo "================================================================================"
echo ""
echo "For more details, use: ./scripts/view-logs.sh [OPTIONS]"
echo "  Examples:"
echo "    ./scripts/view-logs.sh errors          # View all errors"
echo "    ./scripts/view-logs.sh request <ID>    # View specific request"
echo "    ./scripts/view-logs.sh tail            # Follow logs in real-time"
echo ""
