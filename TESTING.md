# Testing Guide

This project includes comprehensive tests to verify the LLM service works correctly.

## Quick Start: Run All Tests

To run all critical tests at once:

```bash
./run_all_tests.sh
```

This will run all tests in order and provide a summary. Individual tests are described below.

## Test Files

### 0. `test_gpu_exclusive.py` - GPU Exclusive Access Test 🆕
**Purpose:** Verifies only one vLLM container is running with exclusive GPU access

**What it tests:**
- ✓ Exactly 1 vLLM container running (prevents GPU memory conflicts)
- ✓ GPU memory allocation and usage
- ✓ Container-specific GPU usage
- ✓ GPU compute mode (shared vs exclusive)
- ✓ Docker GPU device configuration

**Usage:**
```bash
python3 test_gpu_exclusive.py
```

**Setting up exclusive GPU mode:**
```bash
# Run the setup script (requires sudo password)
sudo ./setup_gpu_exclusive.sh

# Or manually:
sudo nvidia-smi -c EXCLUSIVE_PROCESS
```

### 0.5. `test_cors.py` - CORS Configuration Test 🔒 **CRITICAL**
**Purpose:** Prevents regression of CORS headers that breaks browser access

**What it tests:**
- ✓ Authorization header explicitly listed (NOT wildcard `*`)
- ✓ CORS preflight requests work for all endpoints
- ✓ Actual API calls with Authorization header succeed
- ✓ All required CORS headers present

**Why this is critical:**
- Browser CORS spec requires `Authorization` to be explicitly listed
- Using wildcard `*` for `Access-Control-Allow-Headers` does NOT cover `Authorization`
- Without this test, changes could break browser access while curl/Playwright still work

**Usage:**
```bash
python3 test_cors.py
```

**If this test fails:**
The test provides detailed instructions on how to fix the CORS configuration in `router/app/main.py`.

## Test Files

### 1. `test_e2e_playwright.py` - Playwright Browser Tests 🎭 **PRIMARY** ⭐
**Purpose:** Real browser automation - Tests WebUI exactly as a user would interact with it

**What it tests:**
- ✓ Page loads with correct title and all UI elements
- ✓ Model dropdown populated with running models only
- ✓ Send chat message and receive response
- ✓ Streaming response with typing effect
- ✓ Model Manager panel (open/close, view models, start/stop buttons)
- ✓ Create new chat conversation
- ✓ Clear chat functionality
- ✓ Remote access URL works

**Advantages over requests-based tests:**
- ✅ Tests actual JavaScript execution
- ✅ Tests UI rendering and visibility
- ✅ Tests user interactions (clicks, typing)
- ✅ Tests timing and async behavior
- ✅ Can take screenshots on failure
- ✅ Tests exactly what users see

**Usage:**
```bash
# Test from local machine
python3 test_e2e_playwright.py

# Test remote access
python3 test_e2e_playwright.py http://172.30.0.54:3000

# Test from actual remote computer
python3 test_e2e_playwright.py http://<server-ip>:3000

# Run with visible browser (for debugging)
# Edit test file: browser.launch(headless=False)
```

### 2. `test_system_e2e.py` - Requests-based E2E Tests
**Purpose:** API-level validation of user flows (no browser required)

**What it tests:**
- ✓ WebUI HTML loads
- ✓ API discovery from browser context (CORS)
- ✓ Complete chat flow via API calls
- ✓ Streaming chat via SSE
- ✓ Model Manager API endpoints
- ✓ Remote access capability

**Usage:**
```bash
# Test from local machine
python3 test_system_e2e.py

# Test remote access (simulating another computer)
python3 test_system_e2e.py 172.30.0.54

# Test from actual remote computer
python3 test_system_e2e.py <server-ip-address>
```

### 3. `test_service.py` - API Integration Tests
**Purpose:** Tests individual API endpoints

**What it tests:**
- API health endpoint
- Models list endpoint
- Models status endpoint
- Chat completion (non-streaming)
- Streaming chat
- WebUI accessibility
- Model dropdown filtering (only running models)

**Usage:**
```bash
python3 test_service.py
```

### 4. `test_api_curl.sh` - Manual API Tests
**Purpose:** Quick curl-based API validation

**Usage:**
```bash
./test_api_curl.sh
```

## Remote Access Testing

### From This Computer
```bash
# Get your server IP
hostname -I

# Test with that IP
python3 test_system_e2e.py <your-ip>
```

### From Another Computer
1. Ensure firewall allows ports 3000 and 8080
2. Copy `test_system_e2e.py` to the remote computer
3. Run:
   ```bash
   python3 test_system_e2e.py <server-ip>
   ```

### Using a Web Browser (Real User Test)
1. From another computer, open: `http://<server-ip>:3000`
2. Select a model from dropdown (should only show running models)
3. Type a message and click Send
4. Verify streaming response appears
5. Open Model Manager to view/manage models

## Test Coverage

| Test Type | File | What User Does |
|-----------|------|----------------|
| **System E2E** | `test_system_e2e.py` | Opens WebUI, sends chat, sees response |
| **API Integration** | `test_service.py` | Tests backend API directly |
| **Manual Curl** | `test_api_curl.sh` | Quick API verification |

## Expected Results

### All Tests Passing
```
✅ All system tests passed!

Remote Access Instructions:
From another computer, open: http://172.30.0.54:3000
```

### If Tests Fail

**WebUI Not Loading:**
- Check: `docker ps` - ensure `webui-frontend` is running
- Check: Port 3000 is accessible

**API Not Responding:**
- Check: `docker ps` - ensure `vllm-router` is healthy
- Check: Port 8080 is accessible

**No Models Available:**
- Check: `docker ps` - at least one vllm-* container should be healthy
- Check: GPU memory with `nvidia-smi`

**Remote Access Fails:**
- Check firewall allows ports 3000 and 8080
- Verify server IP with `hostname -I`
- Test local access first before remote

## Quick Test Commands

```bash
# GPU exclusive access test (recommended first)
python3 test_gpu_exclusive.py

# CORS configuration test (CRITICAL - prevents browser access issues)
python3 test_cors.py

# Real browser E2E test (RECOMMENDED - most comprehensive)
python3 test_e2e_playwright.py

# Test remote access with real browser
python3 test_e2e_playwright.py http://$(hostname -I | awk '{print $1}'):3000

# API-level E2E test (no browser needed)
python3 test_system_e2e.py

# Quick API check
./test_api_curl.sh

# Comprehensive API tests
python3 test_service.py
```

## Continuous Testing

Run tests after:
- Starting/restarting containers
- Changing configuration (ESPECIALLY router/app/main.py CORS settings)
- Updating code
- Before committing changes
- When troubleshooting issues

**CRITICAL:** Always run `test_cors.py` after any changes to `router/app/main.py`, especially CORS configuration. Browser access can break silently while curl/Playwright tests still pass!
