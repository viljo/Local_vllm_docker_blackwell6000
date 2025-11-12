#!/bin/bash
# Test tool calling API with curl

API_KEY="sk-local-58511ab0d37124beb566b567e54b8307"
BASE_URL="http://localhost:8080/v1"

echo "==========================================================="
echo "TEST 1: Normal Chat Without Tools (Backward Compatibility)"
echo "==========================================================="

curl -s -X POST "$BASE_URL/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [
      {"role": "user", "content": "Say hello in exactly 3 words"}
    ],
    "temperature": 0.1,
    "max_tokens": 20
  }' | python3 -m json.tool

echo ""
echo ""
echo "==========================================================="
echo "TEST 2: Basic Tool Calling"
echo "==========================================================="

curl -s -X POST "$BASE_URL/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss-120b",
    "messages": [
      {"role": "user", "content": "Read the file /tmp/test.txt"}
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "read_file",
          "description": "Read the contents of a file at the specified path",
          "parameters": {
            "type": "object",
            "properties": {
              "path": {
                "type": "string",
                "description": "Absolute or relative path to the file"
              }
            },
            "required": ["path"]
          }
        }
      }
    ],
    "tool_choice": "auto",
    "temperature": 0.1
  }' | python3 -m json.tool

echo ""
echo ""
echo "Done!"
