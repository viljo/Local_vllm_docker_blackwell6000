# Cline Configuration for Local LLM Service

**Updated**: 2025-11-12
**Feature**: Tool Calling Support (003-cline-tool-calling)

## Quick Setup

⚠️ **IMPORTANT**: This is a **network shared service** accessible from multiple computers on your local network.

Your LLM service now supports OpenAI-compatible tool calling! Configure Cline to use it:

### Recommended: Network Configuration (for all computers)

Use this configuration on **all computers** on your network:

```json
{
  "cline.apiProvider": "openai-compatible",
  "cline.openAiCompatible.baseUrl": "http://172.30.0.54:8080/v1",
  "cline.openAiCompatible.apiKey": "sk-local-58511ab0d37124beb566b567e54b8307",
  "cline.openAiCompatible.modelId": "gpt-oss-120b"
}
```

### Setup Methods

**Option 1: VSCode User Settings** (applies to all projects)
1. Open VSCode
2. Press `Ctrl+,` (or `Cmd+,` on Mac) to open Settings
3. Search for "Cline"
4. Click "Edit in settings.json"
5. Add the configuration above

**Option 2: Workspace Settings** (project-specific)
- Already configured in this repo: `.vscode/settings.json`
- Just open this project in VSCode and it will work!

**Option 3: On the Server Machine Only**
If you're on the machine running the service (172.30.0.54), you can use:

```json
{
  "cline.apiProvider": "openai-compatible",
  "cline.openAiCompatible.baseUrl": "http://localhost:8080/v1",
  "cline.openAiCompatible.apiKey": "sk-local-58511ab0d37124beb566b567e54b8307",
  "cline.openAiCompatible.modelId": "gpt-oss-120b"
}
```

## Configuration Details

### API Endpoint (Network Shared Service)
- **Base URL**: `http://172.30.0.54:8080/v1` (use this on all network computers)
- **Alternative**: `http://localhost:8080/v1` (only on server machine)
- **Endpoint**: `/v1/chat/completions`
- **Protocol**: HTTP (local network)
- **Network**: Available to all computers on local network

### Authentication
- **API Key**: `sk-local-58511ab0d37124beb566b567e54b8307`
- **Type**: Bearer token
- **Header**: `Authorization: Bearer <API_KEY>`

### Available Models

| Model ID | Description | GPU Memory | Use Case |
|----------|-------------|------------|----------|
| `gpt-oss-120b` | GPT-OSS 120B | ~120GB | Best quality, tool calling |
| `gpt-oss-20b` | GPT-OSS 20B | ~20GB | Good quality, faster |
| `deepseek-coder-33b-instruct` | DeepSeek Coder | ~33GB | Code-focused |
| `qwen-2.5-14b-instruct` | Qwen 2.5 14B | ~14GB | General purpose |

**Recommended**: `gpt-oss-120b` for best tool calling performance

## Tool Calling Features

Your local LLM service now supports:

✅ **File Operations**
- Read files: `"Read the contents of README.md"`
- Write files: `"Create a new file called test.py with..."`
- List files: `"Show me all Python files in the current directory"`

✅ **Bash Commands**
- Execute commands: `"Run 'ls -la' in the current directory"`
- Check status: `"What's the git status?"`
- Install packages: `"Install httpx using pip"`

✅ **Multi-Turn Conversations**
- Complex workflows with multiple tool calls
- Tool results fed back for processing
- Conversation context maintained

✅ **Parallel Execution**
- Multiple tools can be called simultaneously
- Improved performance for complex operations

## Testing Your Configuration

### Test 1: Simple Chat (No Tools)
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-local-58511ab0d37124beb566b567e54b8307" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'
```

### Test 2: With Tool Calling
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-local-58511ab0d37124beb566b567e54b8307" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [{"role": "user", "content": "List files in /tmp"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "list_files",
        "description": "List files in a directory",
        "parameters": {
          "type": "object",
          "properties": {
            "path": {"type": "string"}
          },
          "required": ["path"]
        }
      }
    }]
  }'
```

### Test 3: Check Service Status
```bash
curl -H "Authorization: Bearer sk-local-58511ab0d37124beb566b567e54b8307" \
  http://localhost:8080/v1/models
```

## Using Cline with Tool Calling

Once configured, try these commands in Cline:

1. **Read a file**:
   - "Read the contents of README.md"
   - "Show me the main.py file"

2. **Create/Edit files**:
   - "Create a new Python script that prints Hello World"
   - "Add error handling to the main function"

3. **Execute commands**:
   - "Run the tests"
   - "Show git status"
   - "Install dependencies from requirements.txt"

4. **Complex workflows**:
   - "Read all Python files, analyze them, and create a summary"
   - "Find all TODO comments in the codebase"

## Troubleshooting

### Cline can't connect to the API

**Check if router is running**:
```bash
docker ps | grep vllm-router
```

**Check router logs**:
```bash
docker logs vllm-router --tail 50
```

**Restart router if needed**:
```bash
docker restart vllm-router
```

### API returns 401 Unauthorized

**Verify API key**:
```bash
docker exec vllm-router env | grep API_KEY
```

Update your Cline settings with the correct API key.

### Model not responding with tool calls

**Possible causes**:
1. Model needs better instructions (gpt-oss-120b works best)
2. Tool definitions need clearer descriptions
3. Model is in a safety mode refusing the operation

**Try**:
- Use more explicit instructions
- Use `gpt-oss-120b` model
- Check router logs for transformation

### Check tool calling is working

**View router logs during request**:
```bash
docker logs vllm-router -f
```

Look for:
- `Chat completion request - ... tools=X` (tools detected)
- `Filtered out unsupported parameters` (tools being processed)
- `Detected X tool call(s)` (tools extracted from response)

## Advanced Configuration

### Custom Model Routing

If you want to use different models for different tasks:

```json
{
  "cline.apiProvider": "openai-compatible",
  "cline.openAiCompatible.baseUrl": "http://localhost:8080/v1",
  "cline.openAiCompatible.apiKey": "sk-local-58511ab0d37124beb566b567e54b8307",
  "cline.openAiCompatible.modelId": "gpt-oss-120b"
}
```

### Streaming Responses

Streaming is automatically enabled. To include usage statistics:

```json
{
  "cline.streamingEnabled": true,
  "cline.includeUsageStats": true
}
```

### Timeout Settings

For long-running operations:

```json
{
  "cline.timeout": 300000
}
```

## Performance Tips

1. **Use gpt-oss-120b for tool calling** - Best at following tool calling format
2. **Keep tool descriptions clear** - Helps model understand when to use them
3. **Use parallel_tool_calls** - Enabled by default for better performance
4. **Monitor GPU usage** - Ensure model has enough VRAM loaded

## Security Notes

⚠️ **Local Network Only**: This setup is for local development. The API key provides full access to your LLM service.

🔒 **API Key**: Keep your API key secure. It's currently: `sk-local-58511ab0d37124beb566b567e54b8307`

🌐 **Network Access**: By default, accessible on your local network. Firewall rules apply.

## Support

- **Documentation**: `/home/asvil/git/local_llm_service/specs/003-cline-tool-calling/`
- **Implementation Details**: `IMPLEMENTATION_COMPLETE.md`
- **API Reference**: `contracts/tool-calling-api.yaml`
- **Testing**: `test_tool_calling_curl.sh`

## Status

✅ **Service Status**: Running
✅ **Tool Calling**: Enabled
✅ **Backward Compatible**: Yes
✅ **Production Ready**: Yes

---

**Last Updated**: 2025-11-12
**Feature Branch**: 003-cline-tool-calling
**Pull Request**: #6
