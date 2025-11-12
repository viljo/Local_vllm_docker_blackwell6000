# Cline Troubleshooting Guide

**Updated**: 2025-11-12
**Service Status**: ✅ Verified Working

## ✅ Verified Working Configuration

⚠️ **IMPORTANT**: This is a **network shared service** accessible from multiple computers.

The API has been tested and confirmed working with all Cline parameters:

**For all computers on the network** (recommended):
```json
{
  "cline.apiProvider": "openai-compatible",
  "cline.openAiCompatible.baseUrl": "http://172.30.0.54:8080/v1",
  "cline.openAiCompatible.apiKey": "sk-local-58511ab0d37124beb566b567e54b8307",
  "cline.openAiCompatible.modelId": "gpt-oss-120b"
}
```

**Only on server machine** (172.30.0.54):
```json
{
  "cline.apiProvider": "openai-compatible",
  "cline.openAiCompatible.baseUrl": "http://localhost:8080/v1",
  "cline.openAiCompatible.apiKey": "sk-local-58511ab0d37124beb566b567e54b8307",
  "cline.openAiCompatible.modelId": "gpt-oss-120b"
}
```

## Common Issues and Solutions

### Issue 1: "API endpoint not responding" or "Connection refused"

**Symptoms**: Cline can't connect to the API

**Check 1 - Is the router running?**
```bash
docker ps | grep vllm-router
```

**Expected Output**:
```
vllm-router    Up XX hours (healthy)
```

**Fix**: If not running, start it:
```bash
docker restart vllm-router
```

---

### Issue 2: "Invalid API key" or "401 Unauthorized"

**Symptoms**: Cline reports authentication failure

**Check - Get the current API key**:
```bash
docker exec vllm-router env | grep API_KEY
```

**Current Key**: `sk-local-58511ab0d37124beb566b567e54b8307`

**Fix**: Update your Cline settings with the correct key.

---

### Issue 3: "Model not found" or "Invalid model"

**Symptoms**: Cline can't find the model

**Check - List available models**:
```bash
curl -H "Authorization: Bearer sk-local-58511ab0d37124beb566b567e54b8307" \
  http://localhost:8080/v1/models | python3 -m json.tool
```

**Available Models**:
- `gpt-oss-120b` ✅ (Recommended for tool calling)
- `gpt-oss-20b`
- `deepseek-coder-33b-instruct`
- `qwen-2.5-14b-instruct`

**Fix**: Use one of the available models in your Cline settings.

---

### Issue 4: Cline says "API functionality not supported"

**Symptoms**: Cline complains about missing features

**This is FIXED** ✅ - Our implementation now supports:
- ✅ Tool calling (`tools`, `tool_choice`, `parallel_tool_calls`)
- ✅ Streaming with usage (`stream_options`)
- ✅ All OpenAI parameters
- ✅ Multi-turn conversations

**Test the API**:
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-local-58511ab0d37124beb566b567e54b8307" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [{"role": "user", "content": "Hello"}],
    "tools": [],
    "tool_choice": "auto",
    "parallel_tool_calls": true,
    "max_tokens": 50
  }'
```

**Expected**: Should return a valid response without errors.

---

### Issue 5: Wrong Base URL

**Important**: This is a **network shared service** - choose the right URL!

**Correct Configuration**:
- ✅ **On ANY computer (including server)**: `http://172.30.0.54:8080/v1` (RECOMMENDED)
- ✅ **Only on server machine (172.30.0.54)**: `http://localhost:8080/v1` (works but not recommended)

**Why use the IP address everywhere?**
- Works on all computers (portable configuration)
- No confusion about which machine you're on
- Easier to share settings files

**Fix**: Update your Cline settings to use `http://172.30.0.54:8080/v1` on all machines

---

### Issue 6: Cline not picking up workspace settings

**Symptoms**: Cline doesn't use your local API despite correct settings

**Solution 1 - Reload VSCode**:
1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. Type "Reload Window"
3. Press Enter

**Solution 2 - Check settings location**:

Workspace settings are here:
```
/home/asvil/git/local_llm_service/.vscode/settings.json
```

User settings (if you prefer global):
- Linux: `~/.config/Code/User/settings.json`
- Mac: `~/Library/Application Support/Code/User/settings.json`
- Windows: `%APPDATA%\Code\User\settings.json`

**Solution 3 - Verify Cline sees the settings**:
1. Open Cline panel in VSCode
2. Click the gear/settings icon
3. Verify it shows your local API URL

---

### Issue 7: Model responds but doesn't use tools

**Symptoms**: Model gives text responses instead of using tools

**This is EXPECTED behavior** for some queries. The model decides when to use tools based on:
1. The user's request
2. The tool descriptions
3. The model's training

**Models ranked by tool-calling ability**:
1. ⭐ `gpt-oss-120b` - Best for tool calling
2. `gpt-oss-20b` - Good, but less consistent
3. `qwen-2.5-14b-instruct` - Decent
4. `deepseek-coder-33b-instruct` - Code-focused, may not use tools

**Tips for better tool calling**:
- Use explicit instructions: "Use the read_file tool to..."
- Use `gpt-oss-120b` model
- Provide clear tool descriptions
- Ask for operations that clearly need tools (file operations, bash commands)

---

### Issue 8: Streaming not working

**Symptoms**: Responses come all at once or hang

**Check**: Streaming is supported and working:
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-local-58511ab0d37124beb566b567e54b8307" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [{"role": "user", "content": "Count to 5"}],
    "stream": true,
    "max_tokens": 50
  }'
```

**Expected**: You should see multiple `data:` lines streaming.

**Fix**: Ensure Cline settings include:
```json
{
  "cline.streamingEnabled": true
}
```

---

## Verification Tests

### Test 1: Basic Connection
```bash
curl http://localhost:8080/health
```
**Expected**: `{"status":"healthy"}`

---

### Test 2: Authentication
```bash
curl -H "Authorization: Bearer sk-local-58511ab0d37124beb566b567e54b8307" \
  http://localhost:8080/v1/models
```
**Expected**: JSON list of models

---

### Test 3: Simple Chat
```bash
cat > /tmp/test.json << 'EOF'
{
  "model": "gpt-oss-120b",
  "messages": [{"role": "user", "content": "Say hello"}],
  "max_tokens": 20
}
EOF

curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-local-58511ab0d37124beb566b567e54b8307" \
  -H "Content-Type: application/json" \
  -d @/tmp/test.json
```
**Expected**: Valid chat completion response

---

### Test 4: Tool Calling (Cline-like request)
```bash
cat > /tmp/test_tools.json << 'EOF'
{
  "model": "gpt-oss-120b",
  "messages": [{"role": "user", "content": "Hello"}],
  "tools": [],
  "tool_choice": "auto",
  "parallel_tool_calls": true,
  "max_tokens": 50
}
EOF

curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-local-58511ab0d37124beb566b567e54b8307" \
  -H "Content-Type: application/json" \
  -d @/tmp/test_tools.json
```
**Expected**: Valid response (tools parameters accepted)

---

## Check Logs for Debugging

### View recent requests:
```bash
docker logs vllm-router --tail 50
```

### Follow logs in real-time:
```bash
docker logs vllm-router -f
```

### Look for errors:
```bash
docker logs vllm-router --tail 200 | grep -E "ERROR|400|401|422|500"
```

### Look for tool calling activity:
```bash
docker logs vllm-router --tail 200 | grep -E "tool|Tool"
```

---

## Quick Reset

If nothing works, try a complete reset:

```bash
# 1. Restart router
docker restart vllm-router

# 2. Wait for startup
sleep 5

# 3. Test API
curl http://localhost:8080/health

# 4. Reload VSCode
# Press Ctrl+Shift+P → "Reload Window"
```

---

## API Specification Summary

**Endpoint**: `http://localhost:8080/v1/chat/completions`

**Supported Parameters** (OpenAI Compatible):
- ✅ `model` - Model identifier
- ✅ `messages` - Conversation history
- ✅ `temperature` - Sampling temperature
- ✅ `max_tokens` - Max generation length
- ✅ `top_p` - Nucleus sampling
- ✅ `stop` - Stop sequences
- ✅ `stream` - Enable streaming
- ✅ `tools` - Tool/function definitions
- ✅ `tool_choice` - Tool selection strategy
- ✅ `parallel_tool_calls` - Allow parallel execution
- ✅ `stream_options` - Streaming configuration

**Response Format**: OpenAI-compatible
- Standard chat completion format
- Tool calls in `message.tool_calls` array
- Usage statistics in `usage` field
- Streaming with Server-Sent Events (SSE)

---

## Still Having Issues?

### Check Service Status
```bash
# Is Docker running?
docker ps

# Is router healthy?
docker ps | grep vllm-router

# Check router resource usage
docker stats vllm-router --no-stream

# Is the model loaded?
curl -H "Authorization: Bearer sk-local-58511ab0d37124beb566b567e54b8307" \
  http://localhost:8080/v1/models/status
```

### Get Help
- **API Documentation**: `/home/asvil/git/local_llm_service/specs/003-cline-tool-calling/`
- **Implementation Details**: `IMPLEMENTATION_COMPLETE.md`
- **Test Script**: `test_tool_calling_curl.sh`

### Report Format
If you need to report an issue, include:
1. Exact Cline error message
2. Output of: `docker logs vllm-router --tail 50`
3. Output of: `curl http://localhost:8080/health`
4. Your Cline settings (`.vscode/settings.json`)

---

**Status**: ✅ All systems operational and tested
**Last Verified**: 2025-11-12 13:40 UTC
**API Version**: With tool calling support (PR #6)
