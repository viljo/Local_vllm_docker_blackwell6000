# Quick Start - Secure Setup

## TL;DR - One Command Setup

```bash
./run.sh start
```

That's it! The script will automatically handle everything, including API key security.

---

## What Happens Automatically

### First Time Setup

When you run `./run.sh start` for the first time:

1. ✅ **Creates .env file** from template
2. ✅ **Generates secure API key** using Python's cryptographic `secrets` module
3. ✅ **Updates .env automatically**
4. ✅ **Starts all services**

```bash
$ ./run.sh start

========================================
  Local LLM Service - Launch Script
========================================

===> Checking Configuration

⚠ .env file not found. Creating from template...
Generating secure API key...
✓ Created .env file with generated API key
  API Key: sk-local-a320fe99954089a09afe89a29a0e262597bacbd0ada454958f4038504b709e1f
  Saved to .env file

===> Starting Services
...
```

### Existing Setup with Weak Key

If you have an old/weak API key, the script detects it:

```bash
$ ./run.sh start

========================================
  Local LLM Service - Launch Script
========================================

===> Checking Configuration

✓ .env file exists
⚠ WARNING: Weak or compromised API key detected!
  Current key: sk-local-dev-key

This key is either:
  • A default/example key from .env.example
  • A previously compromised key
  • Too short to be secure

Generate a new secure API key? [Y/n]:
```

Just press **Enter** and it handles everything:

```bash
Generate a new secure API key? [Y/n]: y
✓ Generated new secure API key
  New API Key: sk-local-b7d8e9f0123456789abcdef0123456789abcdef0123456789abcdef012345678
  Updated in .env file
```

### Existing Setup with Secure Key

If you already have a secure key:

```bash
$ ./run.sh start

========================================
  Local LLM Service - Launch Script
========================================

===> Checking Configuration

✓ .env file exists
✓ API key looks secure
  API Key: sk-local-b...45678

===> Starting Services
...
```

---

## Security Features

### Automatic Detection

The script checks for:

✅ Missing API keys
✅ Weak default keys (`sk-local-dev-key`, etc.)
✅ Compromised keys from previous versions
✅ Keys that are too short (less than 32 hex chars)

### Known Weak Keys Blacklist

These keys are automatically flagged as insecure:
- `sk-local-dev-key`
- `sk-local-your-secret-key-here`
- `sk-local-CHANGE-THIS-TO-A-SECURE-RANDOM-KEY`
- `sk-local-2ac9387d659f7131f38d83e5f7bee469` (compromised from old code)

### Cryptographically Secure Generation

New keys are generated using:
1. **Primary**: Python's `secrets.token_hex(32)` - cryptographically secure
2. **Fallback**: OpenSSL `rand -hex 32` - if Python unavailable

Generated keys have 256 bits of entropy (64 hex characters).

---

## Manual Override

If you prefer to use your own key:

```bash
# Generate manually
python3 -c "import secrets; print('sk-local-' + secrets.token_hex(32))"

# Edit .env file
nano .env

# Add your key
API_KEY=sk-local-YOUR-KEY-HERE

# Start services
./run.sh start
```

Or when prompted by the script, answer `n` to keep your existing key:

```bash
Generate a new secure API key? [Y/n]: n
⚠ Keeping existing API key (not recommended)
```

---

## What's Different from Before?

### Old Behavior (Insecure)
```bash
# API key was hardcoded in frontend JavaScript
const API_KEY = 'sk-local-2ac9387d659f7131f38d83e5f7bee469';

# Visible to anyone in browser DevTools
# Anyone could steal and use the key
```

### New Behavior (Secure)
```bash
# No API key in frontend code at all
# Router handles authentication (BFF pattern)

# For browser/WebUI: No API key needed
Browser → WebUI → Router → vLLM backends

# For external tools: API key required
curl -H "Authorization: Bearer sk-local-YOUR-KEY" \
  http://localhost:8080/v1/models
```

---

## Verification

After setup, verify everything works:

### Check WebUI (No API key needed)
```bash
# Open in browser
http://localhost:3000

# Should work immediately without any API key prompts
```

### Check API Test Page
```bash
# Open test page
http://localhost:3000/test.html

# Click "Test /v1/models" - should work without auth
```

### Check Programmatic Access (API key required)
```bash
# Get your API key
grep "^API_KEY=" .env

# Test with curl
curl -H "Authorization: Bearer YOUR-API-KEY-HERE" \
  http://localhost:8080/v1/models
```

---

## Troubleshooting

### Script says "python3 not found"

If you see this error, the script will use openssl instead. Both are secure.

To install Python 3:
```bash
# Ubuntu/Debian
sudo apt-get install python3

# macOS
brew install python3

# RHEL/CentOS
sudo yum install python3
```

### Want to regenerate API key later

```bash
# Method 1: Delete .env and run script
rm .env
./run.sh start

# Method 2: Edit .env and use weak key, script will detect
echo "API_KEY=sk-local-dev-key" > .env
./run.sh start
# Script will prompt to generate new one

# Method 3: Generate manually and update .env
NEW_KEY=$(python3 -c "import secrets; print('sk-local-' + secrets.token_hex(32))")
sed -i "s/API_KEY=.*/API_KEY=${NEW_KEY}/" .env
```

### Check what key is currently in use

```bash
# Show current key
grep "^API_KEY=" .env

# Or let the script show it
./run.sh status
```

---

## Security Best Practices

✅ **Use the automatic generation** - It's the easiest and most secure
✅ **Never commit .env to git** - It's in .gitignore already
✅ **Rotate keys periodically** - Especially if you suspect compromise
✅ **Don't share keys** - Each deployment should have unique keys
✅ **Keep backups** - Save your .env file in a secure password manager

---

## Summary

The enhanced `run.sh` script makes security effortless:

1. **Automatically detects** weak or missing API keys
2. **Prompts interactively** with sensible defaults
3. **Generates cryptographically secure** keys
4. **Updates configuration** automatically
5. **Validates security** on every startup

Just run `./run.sh start` and follow the prompts. The script does the rest! 🔒

---

## Next Steps

After successful setup:

1. ✅ Explore the WebUI at http://localhost:3000
2. ✅ Read the full migration guide: `SECURITY_FIXES_MIGRATION_GUIDE.md`
3. ✅ Review security analysis: `SECURITY_REVIEW.md`
4. ✅ Configure IDE integration: `docs/ide-integration.md`
5. ✅ Run validation tests: `./scripts/validate-deployment.sh`

Enjoy your secure local LLM service! 🚀
