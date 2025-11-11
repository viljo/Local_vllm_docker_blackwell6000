# Security Review - ChatGPT-like WebUI for Local LLM Service

**Review Date:** 2025-11-11
**Commit:** 8055f4e - "Add ChatGPT-like WebUI for Local LLM Service"
**Branch:** claude/review-mr-security-issues-011CV1oKTykTJxUaeAhNYimG

## Executive Summary

This security review identified **7 security issues** in the recent merge request, including **1 CRITICAL** and **2 HIGH** severity vulnerabilities that require immediate attention before deployment to production.

## Critical Issues

### 1. 🔴 CRITICAL: Hardcoded API Key in Frontend Code

**Severity:** CRITICAL
**CWE:** CWE-798 (Use of Hard-coded Credentials)

**Locations:**
- `frontend/src/hooks/useChat.ts:17`
- `frontend/public/test.html:21`
- `frontend/public/test.html:49`

**Description:**
The API key `sk-local-2ac9387d659f7131f38d83e5f7bee469` is hardcoded directly in the frontend JavaScript/TypeScript code. This is a critical security vulnerability because:

1. The API key is visible in the browser's source code to any user
2. Users can extract the key from network requests in browser DevTools
3. The key is permanently embedded in the production build artifacts
4. Anyone with the key can bypass authentication and access the LLM backend

**Vulnerable Code:**
```typescript
// frontend/src/hooks/useChat.ts:17
const API_KEY = import.meta.env.VITE_API_KEY || 'sk-local-2ac9387d659f7131f38d83e5f7bee469';
```

```html
<!-- frontend/public/test.html:21 -->
<p class="info">API Key: sk-local-2ac9387d659f7131f38d83e5f7bee469</p>

<!-- frontend/public/test.html:49 -->
const API_KEY = 'sk-local-2ac9387d659f7131f38d83e5f7bee469';
```

**Impact:**
- Unauthorized access to LLM models
- Resource abuse and cost implications
- Potential data exfiltration
- Cannot rotate the key without redeploying the entire frontend

**Recommendation:**
1. **NEVER** hardcode API keys in frontend code
2. Implement a backend-for-frontend (BFF) pattern where the frontend communicates with a backend service that holds the API key
3. Use session-based authentication or per-user API keys
4. Immediately rotate the exposed API key
5. Consider implementing proper authentication (OAuth2, JWT, etc.)

**Alternative Architecture:**
```
Browser → WebUI Backend (authenticated sessions) → Router (with API key) → vLLM
```

---

### 2. 🟠 HIGH: Unrestricted CORS Configuration

**Severity:** HIGH
**CWE:** CWE-942 (Overly Permissive Cross-domain Whitelist)

**Location:** `router/app/main.py:82-90`

**Description:**
The CORS middleware is configured to allow requests from ANY origin (`allow_origins=["*"]`), which exposes the API to potential abuse from any website.

**Vulnerable Code:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins - SECURITY ISSUE
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)
```

**Impact:**
- Any website can make requests to your API
- Cross-Site Request Forgery (CSRF) potential
- Increased attack surface for DDoS
- No control over who can access your resources

**Recommendation:**
1. Restrict `allow_origins` to specific trusted domains
2. Use environment variables to configure allowed origins
3. Implement proper authentication and origin validation
4. Consider using `allow_credentials=True` with specific origins for authenticated requests

**Fixed Example:**
```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,
)
```

---

### 3. 🟠 HIGH: API Key Exposed in Docker Build Arguments

**Severity:** HIGH
**CWE:** CWE-526 (Exposure of Sensitive Information Through Environmental Variables)

**Location:** `docker-compose.yml:117`

**Description:**
The API key is passed as a Docker build argument (`VITE_API_KEY`), which means it gets permanently embedded in the Docker image layers. Build arguments are visible in:
- Docker image history (`docker history <image>`)
- Image metadata
- Container registries if pushed

**Vulnerable Code:**
```yaml
webui-frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
    args:
      VITE_API_KEY: ${API_KEY}  # SECURITY ISSUE: Build args are visible in image layers
```

**Impact:**
- API key is permanently stored in Docker image layers
- Anyone with access to the image can extract the key
- Key persists even if environment variable is changed
- Violates secret management best practices

**Recommendation:**
1. **NEVER** pass secrets as build arguments
2. Use runtime environment variables instead
3. Implement proper secret management (e.g., Docker secrets, Kubernetes secrets)
4. For frontend apps, use the BFF pattern mentioned above

---

## Medium Severity Issues

### 4. 🟡 MEDIUM: Weak Default API Key

**Severity:** MEDIUM
**CWE:** CWE-521 (Weak Password Requirements)

**Location:** `router/app/main.py:27`

**Description:**
The default API key `sk-local-dev-key` is predictable and weak.

**Vulnerable Code:**
```python
API_KEY = os.getenv("API_KEY", "sk-local-dev-key")
```

**Recommendation:**
1. Remove default API key in production builds
2. Fail startup if API_KEY is not set (fail-secure principle)
3. Generate strong random keys for development environments

**Fixed Example:**
```python
API_KEY = os.getenv("API_KEY")
if not API_KEY or API_KEY == "sk-local-dev-key":
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError("API_KEY must be set in production")
    logger.warning("Using weak default API key - DEVELOPMENT ONLY")
    API_KEY = "sk-local-dev-key"
```

---

### 5. 🟡 MEDIUM: Overly Permissive Content Security Policy

**Severity:** MEDIUM
**CWE:** CWE-1021 (Improper Restriction of Rendered UI Layers)

**Location:** `frontend/nginx.conf:9`

**Description:**
The Content Security Policy includes `unsafe-inline` and `unsafe-eval`, which defeats much of CSP's XSS protection.

**Vulnerable Code:**
```nginx
add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline' 'unsafe-eval'; ...";
```

**Impact:**
- XSS vulnerabilities can execute arbitrary JavaScript
- CSP protection is largely ineffective
- Reduces defense-in-depth

**Recommendation:**
1. Remove `unsafe-inline` and `unsafe-eval`
2. Use nonces or hashes for inline scripts
3. Refactor code to avoid inline event handlers
4. Use external JavaScript files

---

### 6. 🟡 MEDIUM: No Rate Limiting Implemented

**Severity:** MEDIUM
**CWE:** CWE-770 (Allocation of Resources Without Limits)

**Location:** Entire API (missing protection)

**Description:**
The API has no rate limiting, allowing potential abuse and DoS attacks.

**Impact:**
- Resource exhaustion
- Increased infrastructure costs
- Service degradation for legitimate users
- Potential GPU memory exhaustion

**Recommendation:**
1. Implement rate limiting middleware (e.g., slowapi, fastapi-limiter)
2. Set per-IP and per-API-key limits
3. Consider implementing token bucket or leaky bucket algorithms
4. Add monitoring and alerting for unusual usage patterns

**Example Implementation:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["100/hour"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/v1/chat/completions")
@limiter.limit("10/minute")
async def chat_completions(...):
    ...
```

---

## Low Severity Issues

### 7. 🟢 LOW: Timing Attack on API Key Comparison

**Severity:** LOW
**CWE:** CWE-208 (Observable Timing Discrepancy)

**Location:** `router/app/main.py:109`

**Description:**
The API key comparison uses string inequality (`!=`), which is vulnerable to timing attacks.

**Vulnerable Code:**
```python
def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    if credentials.credentials != API_KEY:  # Timing attack vulnerability
        raise HTTPException(...)
```

**Recommendation:**
Use constant-time comparison to prevent timing attacks:

```python
import secrets

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    if not secrets.compare_digest(credentials.credentials, API_KEY):
        raise HTTPException(...)
```

---

### 8. 🟢 LOW: Insufficient Input Validation

**Severity:** LOW
**CWE:** CWE-20 (Improper Input Validation)

**Location:** `router/app/main.py:259-263`

**Description:**
Limited validation on user inputs like message content length and max_tokens upper bounds.

**Recommendation:**
1. Add maximum message length validation
2. Validate max_tokens has an upper bound
3. Validate message count per conversation
4. Sanitize model names before routing

**Example:**
```python
class ChatCompletionRequest(BaseModel):
    model: str = Field(..., max_length=100)
    messages: List[ChatMessage] = Field(..., max_items=100)
    max_tokens: Optional[int] = Field(None, gt=0, le=8192)

    @validator('messages')
    def validate_message_content(cls, messages):
        for msg in messages:
            if len(msg.content) > 10000:  # 10KB limit
                raise ValueError("Message content too long")
        return messages
```

---

## Additional Security Recommendations

### 9. Missing Security Headers
Add additional security headers to nginx configuration:
```nginx
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

### 10. Logging Sensitive Information
Review logs to ensure API keys and sensitive data are not logged. The current implementation logs client IPs which is good, but ensure no tokens or keys are logged.

### 11. HTTPS/TLS
The current configuration uses HTTP. For production:
- Implement TLS/HTTPS with valid certificates
- Use HSTS headers
- Redirect HTTP to HTTPS

### 12. Authentication & Authorization
Consider implementing:
- Multi-user support with per-user API keys
- Role-based access control (RBAC)
- OAuth2 or JWT-based authentication
- Session management

---

## Priority Action Items

### Immediate (Before Production Deployment)
1. ✅ Remove hardcoded API keys from frontend code
2. ✅ Implement backend-for-frontend pattern for API key management
3. ✅ Rotate the exposed API key `sk-local-2ac9387d659f7131f38d83e5f7bee469`
4. ✅ Restrict CORS origins to specific trusted domains
5. ✅ Remove API key from Docker build arguments

### Short Term (Within 1 Week)
1. Implement rate limiting
2. Add proper input validation
3. Improve CSP configuration
4. Add security headers
5. Use constant-time API key comparison

### Medium Term (Within 1 Month)
1. Implement proper authentication system
2. Add HTTPS/TLS support
3. Implement comprehensive logging and monitoring
4. Add security testing to CI/CD pipeline
5. Conduct penetration testing

---

## Testing Recommendations

1. **Security Scanning:**
   - Run SAST tools (Bandit for Python, ESLint security plugins for TypeScript)
   - Run dependency vulnerability scanning (Safety, npm audit)
   - Scan Docker images for vulnerabilities (Trivy, Grype)

2. **Manual Testing:**
   - Attempt to extract API key from frontend
   - Test CORS bypass attempts
   - Test rate limiting once implemented
   - Test input validation boundaries

3. **Automated Testing:**
   - Add security tests to test suite
   - Test authentication/authorization edge cases
   - Test error handling doesn't leak sensitive info

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)

---

## Conclusion

This application has several critical security vulnerabilities that must be addressed before production deployment. The most critical issue is the hardcoded API key in the frontend, which completely bypasses authentication and exposes the entire API to unauthorized access.

**Recommendation:** Do not deploy to production until at least the CRITICAL and HIGH severity issues are resolved.
