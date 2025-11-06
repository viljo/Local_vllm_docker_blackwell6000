# IDE Integration Guide

This guide shows how to configure popular IDEs and code editors to use the Local LLM Service.

## Prerequisites

- Local LLM Service running on `http://localhost:8080`
- API key from `.env` file (default: check your configuration)
- At least one model loaded and ready (verify with `curl http://localhost:8080/ready`)

## Quick Reference

| IDE/Editor | Plugin/Extension | Config Location |
|------------|-----------------|-----------------|
| VS Code | Continue.dev | `~/.continue/config.json` |
| Cursor | Built-in | Settings → Models → OpenAI |
| JetBrains | AI Assistant | Settings → Tools → AI Assistant |
| Neovim | copilot.lua / cmp-ai | `~/.config/nvim/lua/` |
| Emacs | gptel | `~/.emacs.d/init.el` |

---

## VS Code

### Option 1: Continue.dev Extension (Recommended)

**Install Extension:**
1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "Continue"
4. Click Install

**Configure:**
1. Press Ctrl+Shift+P (Cmd+Shift+P on Mac)
2. Type "Continue: Open config.json"
3. Add configuration:

```json
{
  "models": [
    {
      "title": "Local Python Coder",
      "provider": "openai",
      "model": "deepseek-coder-33b-instruct",
      "apiBase": "http://localhost:8080/v1",
      "apiKey": "YOUR_API_KEY_HERE"
    },
    {
      "title": "Local General",
      "provider": "openai",
      "model": "mistral-7b-v0.1",
      "apiBase": "http://localhost:8080/v1",
      "apiKey": "YOUR_API_KEY_HERE"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Local Python Coder",
    "provider": "openai",
    "model": "deepseek-coder-33b-instruct",
    "apiBase": "http://localhost:8080/v1",
    "apiKey": "YOUR_API_KEY_HERE"
  }
}
```

**Usage:**
- Press `Ctrl+L` (Cmd+L on Mac) to open chat
- Press `Ctrl+I` (Cmd+I on Mac) for inline edit
- Select code and press `Ctrl+L` to ask questions about it

### Option 2: GitHub Copilot Chat (OpenAI Compatible)

**Configure:**
1. Install GitHub Copilot Chat extension
2. Add to VS Code `settings.json`:

```json
{
  "github.copilot.advanced": {
    "debug.overrideEngine": "gpt-4",
    "debug.overrideProxyUrl": "http://localhost:8080/v1"
  }
}
```

---

## Cursor IDE

Cursor has built-in support for custom OpenAI-compatible endpoints.

**Configure:**
1. Open Cursor Settings (Ctrl+, or Cmd+,)
2. Search for "OpenAI"
3. Configure:
   - **API Base URL**: `http://localhost:8080/v1`
   - **API Key**: `YOUR_API_KEY_HERE`
   - **Model**: `deepseek-coder-33b-instruct`

**Alternative: Using .cursorrules**

Create a `.cursorrules` file in your project root:

```
API_BASE_URL=http://localhost:8080/v1
API_KEY=YOUR_API_KEY_HERE
MODEL=deepseek-coder-33b-instruct
```

**Usage:**
- Press `Ctrl+K` (Cmd+K on Mac) to open chat
- Press `Ctrl+L` (Cmd+L on Mac) for inline suggestions
- Highlight code and press `Ctrl+K` to ask questions

---

## JetBrains IDEs (PyCharm, IntelliJ IDEA, WebStorm, etc.)

### AI Assistant Plugin

**Install Plugin:**
1. Go to Settings → Plugins
2. Search for "AI Assistant"
3. Click Install and restart IDE

**Configure:**
1. Go to Settings → Tools → AI Assistant
2. Select "Custom OpenAI Provider"
3. Configure:
   - **URL**: `http://localhost:8080/v1`
   - **API Key**: `YOUR_API_KEY_HERE`
   - **Model**: `deepseek-coder-33b-instruct`

**Usage:**
- Press `Ctrl+\` (Cmd+\ on Mac) to open AI chat
- Right-click code → AI Actions → Explain Code
- Select code → Alt+Enter → Ask AI

---

## Neovim

### Option 1: copilot.lua (Recommended)

**Install via lazy.nvim:**

```lua
{
  "zbirenbaum/copilot.lua",
  config = function()
    require('copilot').setup({
      panel = { enabled = false },
      suggestion = {
        enabled = true,
        auto_trigger = true,
        debounce = 75,
      },
      filetypes = {
        python = true,
        javascript = true,
        typescript = true,
        lua = true,
        ["*"] = false,
      },
      server_opts_overrides = {
        trace = "verbose",
        settings = {
          advanced = {
            inlineSuggestCount = 3,
          },
          openaiUrl = "http://localhost:8080/v1",
          openaiModel = "deepseek-coder-33b-instruct",
          openaiApiKey = "YOUR_API_KEY_HERE",
        },
      },
    })
  end,
}
```

### Option 2: cmp-ai with nvim-cmp

```lua
{
  "tzachar/cmp-ai",
  dependencies = "nvim-lua/plenary.nvim",
  config = function()
    local cmp_ai = require('cmp_ai.config')
    cmp_ai:setup({
      max_lines = 100,
      provider = 'OpenAI',
      provider_options = {
        base_url = 'http://localhost:8080/v1',
        api_key = 'YOUR_API_KEY_HERE',
        model = 'deepseek-coder-33b-instruct',
      },
      notify = true,
      run_on_every_keystroke = true,
    })
  end,
}
```

**Usage:**
- Inline suggestions appear automatically as you type
- Accept suggestion with `Tab` or custom keybinding

---

## Emacs

### gptel Package

**Install via use-package:**

```elisp
(use-package gptel
  :ensure t
  :config
  (setq gptel-api-key "YOUR_API_KEY_HERE")
  (setq gptel-model "deepseek-coder-33b-instruct")
  (setq gptel-backend
        (gptel-make-openai "Local LLM"
          :host "localhost:8080"
          :endpoint "/v1/chat/completions"
          :stream t
          :key "YOUR_API_KEY_HERE"
          :models '("deepseek-coder-33b-instruct" "mistral-7b-v0.1"))))
```

**Usage:**
- `M-x gptel` to open chat buffer
- Select region and `M-x gptel-send` to ask about code
- `M-x gptel-menu` for more options

---

## Sublime Text

### LSP-Copilot Plugin

**Install:**
1. Install Package Control if not already installed
2. Install LSP and LSP-copilot packages

**Configure (`Packages/User/LSP-copilot.sublime-settings`):**

```json
{
  "settings": {
    "openai.api_base": "http://localhost:8080/v1",
    "openai.api_key": "YOUR_API_KEY_HERE",
    "openai.model": "deepseek-coder-33b-instruct"
  }
}
```

---

## Testing Your Configuration

### Verify Endpoint Access

```bash
# Check service is running
curl http://localhost:8080/health

# Check models are loaded
curl http://localhost:8080/ready

# Test chat completion
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  -d '{
    "model": "deepseek-coder-33b-instruct",
    "messages": [{"role": "user", "content": "Write hello world in Python"}],
    "max_tokens": 100,
    "stream": false
  }'
```

### IDE Test Checklist

- [ ] IDE can connect to local service (no connection errors)
- [ ] Completions are generated (may be slow on first request)
- [ ] Streaming works (tokens appear progressively)
- [ ] Multiple requests work (no rate limiting)
- [ ] Code context is included in requests

---

## Troubleshooting

### Connection Refused

**Symptom:** IDE shows "Connection refused" or "ECONNREFUSED"

**Solution:**
1. Verify service is running: `docker compose ps`
2. Check router logs: `docker compose logs vllm-router`
3. Test endpoint: `curl http://localhost:8080/health`

### Slow Responses

**Symptom:** First completion takes 10+ seconds

**Causes:**
- Model still loading (check `docker compose logs vllm-coder`)
- Cold start (first request allocates KV cache)
- Large context window

**Solutions:**
- Wait for models to fully load (5-10 minutes after startup)
- Subsequent requests will be faster
- Reduce context window in IDE settings

### Invalid API Key

**Symptom:** 401 Unauthorized responses

**Solution:**
1. Check `.env` file for correct `API_KEY`
2. Verify IDE configuration uses same key
3. Ensure no extra spaces or quotes in key

### Model Not Found

**Symptom:** "Model 'X' not found" error

**Solution:**
Use exact model names:
- `deepseek-coder-33b-instruct` (Python coding)
- `mistral-7b-v0.1` (general purpose)

Check available models:
```bash
curl http://localhost:8080/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY_HERE"
```

### Incomplete Responses

**Symptom:** Responses cut off mid-sentence

**Cause:** `max_tokens` limit reached

**Solution:**
- Increase `max_tokens` in IDE settings (try 512 or 1024)
- Reduce conversation history to save tokens

---

## Advanced Configuration

### Custom System Prompts

Some IDEs allow custom system prompts to guide model behavior:

**For Python coding:**
```
You are an expert Python developer. Provide concise, idiomatic Python code following PEP 8 style guidelines. Include type hints and docstrings.
```

**For general assistance:**
```
You are a helpful coding assistant. Provide clear explanations and working code examples.
```

### Context Window Management

To avoid token limit errors:

1. **Reduce conversation history**: Most IDEs have a setting for max messages
2. **Clear context regularly**: Start new chat sessions for unrelated topics
3. **Monitor token usage**: Check router logs for token counts

### Performance Optimization

**For faster completions:**
- Use shorter prompts
- Reduce `max_tokens` to minimum needed
- Disable streaming if not needed
- Clear conversation history frequently

**For better quality:**
- Provide more context in prompts
- Use higher `temperature` for creativity (0.7-0.9)
- Use lower `temperature` for deterministic code (0.1-0.3)

---

## Next Steps

- **Monitor usage**: Check logs with `docker compose logs -f vllm-router`
- **Tune performance**: Adjust parameters in `.env` file
- **Scale up**: Add more GPU capacity for higher throughput
- **Secure access**: Add HTTPS via nginx reverse proxy for remote access

For more details, see:
- [Quickstart Guide](./quickstart.md)
- [API Documentation](../specs/001-vllm-webui-service/contracts/openai-api.yaml)
- [Troubleshooting Guide](./quickstart.md#troubleshooting)
