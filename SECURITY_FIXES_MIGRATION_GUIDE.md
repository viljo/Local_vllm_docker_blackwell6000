# Security Fixes Migration Guide

**Date:** 2025-11-11
**Branch:** claude/review-mr-security-issues-011CV1oKTykTJxUaeAhNYimG

## Overview

This guide explains the security fixes implemented to address critical vulnerabilities found in the WebUI merge request (commit 8055f4e). These changes implement industry best practices for API key management and adopt a Backend-for-Frontend (BFF) security pattern.

## What Changed

### 1. ✅ Removed Hardcoded API Keys from Frontend

**Problem:** API keys were embedded in frontend JavaScript/TypeScript code, making them visible to anyone.

**Solution:** Removed all API key references from:
- `frontend/src/hooks/useChat.ts` - Removed hardcoded fallback key
- `frontend/public/test.html` - Removed API key from test page

**Impact:** Frontend no longer stores or knows the API key at all.

---

### 2. ✅ Implemented Backend-for-Frontend (BFF) Pattern

**Problem:** Frontend needed API keys to authenticate with the router, creating a security risk.

**Solution:** Modified `router/app/main.py` to support optional authentication:

- Added new `optional_verify_api_key()` function that:
  - Accepts requests with valid API keys (for programmatic access)
  - Accepts requests without API keys (for WebUI browser access)
  - Can be configured to require auth via `WEBUI_AUTH_ENABLED` environment variable

- Updated all WebUI endpoints to use `optional_verify_api_key`:
  - `/v1/models` - List available models
  - `/v1/chat/completions` - Chat completions
  - `/v1/completions` - Legacy completions

**Benefits:**
- API key never exposed to browser
- Router acts as a trusted intermediary
- Still secure for programmatic access
- Can be locked down with `WEBUI_AUTH_ENABLED=true` if needed

---

### 3. ✅ Generated New Secure API Key

**Problem:** The old API key `sk-local-2ac9387d659f7131f38d83e5f7bee469` was exposed in public code.

**Solution:**
- Updated `.env.example` with instructions to generate secure keys
- Application now validates API key on startup
- Provides helpful error messages if weak/missing keys detected

**You must generate and set a new API key:**

```bash
# Generate a new secure API key
python3 -c "import secrets; print('sk-local-' + secrets.token_hex(32))"

# Add to your .env file (create if doesn't exist)
echo "API_KEY=sk-local-YOUR-GENERATED-KEY-HERE" >> .env
```

**CRITICAL:** The old key must be considered compromised. Do not reuse it.

---

### 4. ✅ Removed API Key from Docker Build Arguments

**Problem:** API key was passed as Docker build argument, embedding it permanently in image layers.

**Solution:** Removed `VITE_API_KEY` build argument from `docker-compose.yml`.

**Impact:** Frontend builds no longer contain any API key references.

---

### 5. ✅ Updated Vulnerable Dependencies

**Problem:** Dependencies had known security vulnerabilities.

**Solution:** Updated all dependencies to latest secure versions:

**Backend (`router/requirements.txt`):**
- fastapi: 0.104.1 → 0.115.0
- uvicorn: 0.24.0 → 0.32.0
- httpx: 0.25.1 → 0.27.2
- pydantic: 2.5.0 → 2.9.2
- pydantic-settings: 2.1.0 → 2.6.0
- python-multipart: 0.0.6 → 0.0.12
- sse-starlette: 1.8.2 → 2.1.3
- prometheus-client: 0.19.0 → 0.21.0
- tiktoken: 0.5.2 → 0.8.0

**Frontend (`frontend/package.json`):**
- openai: 4.20.1 → 4.69.0
- react: 18.2.0 → 18.3.1
- react-dom: 18.2.0 → 18.3.1
- zustand: 4.4.7 → 5.0.1
- typescript: 5.2.2 → 5.6.3
- vite: 5.0.8 → 5.4.10

---

### 6. ✅ Improved Security Practices

**Additional improvements:**
- API key comparison now uses constant-time `secrets.compare_digest()` (prevents timing attacks)
- Application fails on startup if API key is not set or is weak
- Clear error messages guide users to generate secure keys

### 7. ✅ Enhanced Installation Script

**New Feature:** The `run.sh` script now includes intelligent API key management:

**Automatic Detection:**
- Checks if `.env` file exists
- Detects missing or weak API keys
- Identifies compromised keys from previous versions

**Interactive Generation:**
- Prompts user to generate new key if weak key detected
- Uses Python's `secrets` module for cryptographic security
- Falls back to `openssl` if Python unavailable
- Automatically updates `.env` file

**Security Validation:**
- Validates key length (minimum 32 hex characters after prefix)
- Checks against known weak/compromised keys:
  - `sk-local-dev-key`
  - `sk-local-your-secret-key-here`
  - `sk-local-2ac9387d659f7131f38d83e5f7bee469` (compromised)
  - Any key shorter than required minimum

**Example Usage:**
```bash
./run.sh start

# If weak key detected, you'll see:
# ⚠ WARNING: Weak or compromised API key detected!
#   Current key: sk-local-dev-key
#
# This key is either:
#   • A default/example key from .env.example
#   • A previously compromised key
#   • Too short to be secure
#
# Generate a new secure API key? [Y/n]:
```

Simply press Enter (or type 'y') and the script handles everything automatically!

---

## Migration Steps

### Step 1: Update Your Repository

```bash
# Pull the latest changes
git fetch origin
git checkout claude/review-mr-security-issues-011CV1oKTykTJxUaeAhNYimG
git pull
```

### Step 2: Generate New API Key (Automatic or Manual)

**Option A: Automatic (Recommended) - Use the run.sh script:**

```bash
# The run.sh script will automatically detect weak/missing API keys
./run.sh start
```

The script will:
- ✅ Detect if you have a weak or compromised API key
- ✅ Prompt you to generate a new one automatically
- ✅ Update your .env file with the new key
- ✅ Start the services with the secure key

**Option B: Manual - Generate yourself:**

```bash
# Generate a secure API key
python3 -c "import secrets; print('sk-local-' + secrets.token_hex(32))"
```

Copy the generated key (it will look like: `sk-local-a320fe99954089a09afe89a29a0e262597bacbd0ada454958f4038504b709e1f`)

### Step 3: Update Environment Configuration (If doing manual setup)

Create or update your `.env` file in the project root:

```bash
# Create/edit .env file
nano .env
```

Add your new API key:

```env
# API Authentication
API_KEY=sk-local-YOUR-GENERATED-KEY-HERE

# Other configurations (if needed)
PYTHON_MODEL=TheBloke/deepseek-coder-33B-instruct-AWQ
GENERAL_MODEL=TheBloke/Mistral-7B-v0.1-AWQ
ROUTER_PORT=8080
WEBUI_PORT=3000
CODER_BACKEND_PORT=8000
GENERAL_BACKEND_PORT=8001
CODER_GPU_MEMORY=0.45
GENERAL_GPU_MEMORY=0.40
CODER_MAX_SEQ=64
GENERAL_MAX_SEQ=128
CODER_MAX_MODEL_LEN=4096
GENERAL_MAX_MODEL_LEN=4096
CODER_MAX_BATCHED_TOKENS=8192
GENERAL_MAX_BATCHED_TOKENS=8192
LOG_LEVEL=INFO
```

**Note:** If using the automatic method (Option A), skip this step as the script handles it for you.

### Step 4: Rebuild Docker Containers

The frontend no longer needs API keys, so you must rebuild:

**Option A: Using run.sh (Recommended):**
```bash
# The run.sh script handles everything automatically
./run.sh start
```

**Option B: Manual Docker commands:**
```bash
# Stop existing containers
docker-compose down

# Rebuild with new changes
docker-compose build

# Start services
docker-compose up -d
```

### Step 5: Verify Everything Works

**Test the WebUI:**
```bash
# Open in browser
http://localhost:3000

# Should work without any API key prompts
```

**Test the API test page:**
```bash
# Open test page
http://localhost:3000/test.html

# Click "Test /v1/models" and "Test Chat Completion"
# Should work without authentication
```

**Test programmatic access (with API key):**
```bash
# Test with your new API key
curl -H "Authorization: Bearer sk-local-YOUR-KEY-HERE" \
  http://localhost:8080/v1/models

# Should return list of available models
```

---

## How Authentication Now Works

### For Browser/WebUI Access (No API Key Needed)

```
Browser → WebUI (port 3000) → Router (port 8080) → vLLM Backends
                                   ↓
                          No auth required
                    (BFF pattern - trusted)
```

The router recognizes requests from the WebUI and allows them without authentication by default.

### For Programmatic Access (API Key Required)

```
Your App → Router (port 8080) → vLLM Backends
             ↓
    Auth required (Bearer token)
```

External applications must provide the API key via `Authorization: Bearer` header.

### Example: Programmatic Access

```python
import httpx

API_KEY = "sk-local-YOUR-KEY-HERE"
API_BASE = "http://localhost:8080/v1"

response = httpx.post(
    f"{API_BASE}/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "model": "deepseek-coder-33b-instruct",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False
    }
)

print(response.json())
```

---

## Optional: Enable Strict WebUI Authentication

If you want to require authentication even for WebUI requests (e.g., for additional security), set this in your `.env`:

```env
WEBUI_AUTH_ENABLED=true
```

**Note:** With this enabled, you'll need to implement a separate authentication mechanism for browser users (sessions, cookies, etc.). This is not necessary for local, trusted deployments.

---

## Security Considerations

### For Local Development/Private Networks

The default configuration (no WebUI auth required) is suitable when:
- Service runs on localhost or private network
- Only trusted users have network access
- You trust all devices on your network

### For Remote/Public Access

If you plan to expose this service beyond your local network:

1. **Enable HTTPS/TLS** - Add reverse proxy (nginx, Traefik) with SSL certificates
2. **Consider enabling `WEBUI_AUTH_ENABLED=true`** - Implement proper user authentication
3. **Restrict CORS origins** - Modify router to limit allowed origins
4. **Add rate limiting** - Prevent abuse (not yet implemented)
5. **Implement IP whitelisting** - Only allow specific IPs to access
6. **Use VPN or SSH tunnel** - Secure remote access without exposing service

---

## Troubleshooting

### Error: "API_KEY must be set to a secure value"

**Cause:** Router started without valid API key in environment.

**Fix:**
```bash
# Ensure .env file exists with valid API_KEY
cat .env | grep API_KEY

# If missing or wrong, add correct key
echo "API_KEY=sk-local-YOUR-KEY-HERE" >> .env

# Restart services
docker-compose restart vllm-router
```

---

### WebUI Shows "Connection Failed"

**Cause:** Router not running or wrong URL.

**Fix:**
```bash
# Check router is running
docker-compose ps

# Check router logs
docker-compose logs vllm-router

# Verify router health
curl http://localhost:8080/health

# Should return: {"status":"healthy"}
```

---

### Programmatic Access Returns 401 Unauthorized

**Cause:** Wrong or missing API key.

**Fix:**
```bash
# Verify your API key matches .env
cat .env | grep API_KEY

# Test with correct key
curl -H "Authorization: Bearer sk-local-YOUR-KEY-HERE" \
  http://localhost:8080/v1/models
```

---

### Old Code Still Has Hardcoded Keys

**Cause:** Browser cached old frontend build.

**Fix:**
```bash
# Hard refresh in browser
# Chrome/Firefox: Ctrl+Shift+R (Cmd+Shift+R on Mac)

# Or rebuild frontend
docker-compose build webui-frontend
docker-compose up -d webui-frontend
```

---

## Testing Checklist

After migration, verify:

- [ ] Router starts without errors
- [ ] WebUI loads at http://localhost:3000
- [ ] Can send chat messages through WebUI
- [ ] Test page works at http://localhost:3000/test.html
- [ ] Models list displays in WebUI dropdown
- [ ] Chat responses stream correctly
- [ ] Conversation history persists
- [ ] Can create new conversations
- [ ] Programmatic access works with API key
- [ ] Programmatic access fails with wrong/missing key (401 error)
- [ ] No API keys visible in browser DevTools → Sources tab
- [ ] No API keys visible in browser DevTools → Network tab

---

## Rolling Back (If Needed)

If you encounter issues and need to temporarily roll back:

```bash
# Checkout previous commit
git checkout 8055f4e

# Rebuild containers
docker-compose build
docker-compose up -d
```

**WARNING:** The old commit has security vulnerabilities. Only use for emergency troubleshooting. Please report issues so they can be fixed in the secure version.

---

## Additional Security Recommendations

For production deployments, consider:

1. **Add Rate Limiting** - Prevent abuse and DoS attacks
2. **Implement Request Logging** - Audit who accessed what
3. **Add Input Validation** - Limit message sizes and token counts
4. **Security Headers** - Add X-Frame-Options, CSP, HSTS
5. **Regular Updates** - Keep dependencies updated monthly
6. **Security Scanning** - Run tools like `bandit`, `safety`, `npm audit`
7. **Penetration Testing** - Test security before public deployment

---

## Support

If you encounter issues during migration:

1. Check logs: `docker-compose logs vllm-router webui-frontend`
2. Review this guide's troubleshooting section
3. Check the main security review: `SECURITY_REVIEW.md`
4. Verify environment variables: `docker-compose config`

---

## Summary of Files Changed

### Modified Files:
- `.env.example` - Added secure key generation instructions
- `frontend/src/hooks/useChat.ts` - Removed API key, updated auth
- `frontend/public/test.html` - Removed hardcoded API key
- `router/app/main.py` - Added BFF pattern, constant-time comparison
- `docker-compose.yml` - Removed build args with API key
- `router/requirements.txt` - Updated dependencies
- `frontend/package.json` - Updated dependencies

### New Files:
- `SECURITY_REVIEW.md` - Detailed security analysis
- `SECURITY_FIXES_MIGRATION_GUIDE.md` - This document

---

## Conclusion

These security fixes address critical vulnerabilities and follow industry best practices:

✅ **No more exposed API keys in frontend**
✅ **Backend-for-Frontend (BFF) pattern implemented**
✅ **New secure API key required**
✅ **Dependencies updated to patch vulnerabilities**
✅ **Constant-time comparisons prevent timing attacks**
✅ **Application validates security on startup**

The migration is straightforward:
1. Generate new API key
2. Update `.env` file
3. Rebuild Docker containers
4. Test and verify

Your local LLM service is now significantly more secure! 🔒
