#!/bin/bash
# Comprehensive API tests using curl

API_BASE_URL="http://localhost:8080"

# Load API key from .env file
if [[ -f .env ]]; then
    API_KEY=$(grep "^API_KEY=" .env | cut -d'=' -f2-)
else
    echo "Error: .env file not found. Please create it from .env.example"
    exit 1
fi

if [[ -z "$API_KEY" ]]; then
    echo "Error: API_KEY not found in .env file"
    exit 1
fi

echo "======================================="
echo "LLM API Functional Test Suite"
echo "======================================="
echo ""

# Test 1: Basic math question
echo "Test 1: Basic Math Question"
echo "----------------------------"
RESPONSE=$(curl -s -X POST "${API_BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [{"role": "user", "content": "What is 2+2? Answer with just the number."}],
    "max_tokens": 10,
    "temperature": 0.1
  }')

if echo "$RESPONSE" | grep -q "choices"; then
  echo "✓ Request successful"
  echo "Question: What is 2+2?"
  echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print('Answer:', data['choices'][0]['message']['content'].strip()); print('Tokens:', data['usage']['total_tokens'])"
else
  echo "✗ Request failed"
  echo "$RESPONSE"
fi
echo ""

# Test 2: Code generation
echo "Test 2: Code Generation"
echo "----------------------------"
RESPONSE=$(curl -s -X POST "${API_BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [{"role": "user", "content": "Write a Python function that returns Hello World. Just show the code."}],
    "max_tokens": 100,
    "temperature": 0.3
  }')

if echo "$RESPONSE" | grep -q "choices"; then
  echo "✓ Request successful"
  echo "Question: Write a Python function that returns Hello World"
  echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print('Answer:'); print(data['choices'][0]['message']['content'])"
else
  echo "✗ Request failed"
  echo "$RESPONSE"
fi
echo ""

# Test 3: Reasoning question
echo "Test 3: Reasoning Question"
echo "----------------------------"
RESPONSE=$(curl -s -X POST "${API_BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [{"role": "user", "content": "If I have 3 apples and buy 2 more, how many apples do I have? Answer briefly."}],
    "max_tokens": 50,
    "temperature": 0.1
  }')

if echo "$RESPONSE" | grep -q "choices"; then
  echo "✓ Request successful"
  echo "Question: If I have 3 apples and buy 2 more, how many apples do I have?"
  echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print('Answer:', data['choices'][0]['message']['content'].strip())"
else
  echo "✗ Request failed"
  echo "$RESPONSE"
fi
echo ""

# Test 4: Streaming chat
echo "Test 4: Streaming Chat"
echo "----------------------------"
echo "Question: Count from 1 to 3"
echo "Streaming response:"
curl -s -N -X POST "${API_BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [{"role": "user", "content": "Count from 1 to 3, one number per line. No other text."}],
    "max_tokens": 50,
    "temperature": 0.1,
    "stream": true
  }' | while IFS= read -r line; do
    if [[ "$line" == data:* ]] && [[ "$line" != *"[DONE]"* ]]; then
      echo "$line" | sed 's/^data: //' | python3 -c "import sys, json;
try:
    data=json.load(sys.stdin)
    content=data.get('choices', [{}])[0].get('delta', {}).get('content', '')
    if content: print(content, end='', flush=True)
except: pass" 2>/dev/null
    fi
  done
echo ""
echo "✓ Streaming completed"
echo ""

# Test 5: Models list
echo "Test 5: Models List"
echo "----------------------------"
RESPONSE=$(curl -s -X GET "${API_BASE_URL}/v1/models" \
  -H "Authorization: Bearer ${API_KEY}")

if echo "$RESPONSE" | grep -q "data"; then
  echo "✓ Models endpoint working"
  echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print('Available models:', ', '.join([m['id'] for m in data['data']]))"
else
  echo "✗ Models endpoint failed"
  echo "$RESPONSE"
fi
echo ""

# Test 6: Model status
echo "Test 6: Model Status"
echo "----------------------------"
RESPONSE=$(curl -s -X GET "${API_BASE_URL}/v1/models/status" \
  -H "Authorization: Bearer ${API_KEY}")

if echo "$RESPONSE" | grep -q "models"; then
  echo "✓ Status endpoint working"
  echo "$RESPONSE" | python3 -c "
import sys, json
data=json.load(sys.stdin)
for name, status in data['models'].items():
    state = status.get('status')
    health = status.get('health', 'N/A')
    print(f'  {name}: {state} (health: {health})')
"
else
  echo "✗ Status endpoint failed"
  echo "$RESPONSE"
fi
echo ""

echo "======================================="
echo "All API tests completed"
echo "======================================="
