# Data Model: Local AI Service

**Feature**: 001-vllm-webui-service
**Date**: 2025-10-30
**Phase**: 1 - Design

## Overview

This document defines the key entities, their attributes, relationships, and state transitions for the Local AI Service. Note: This service has minimal persistent state - most data is ephemeral (in-memory queues, session storage).

## Entity Definitions

### 1. Model

Represents an AI language model loaded into vLLM service.

**Attributes**:
- `id` (string): Unique identifier (e.g., "deepseek-coder-33b-instruct")
- `name` (string): Display name for UI
- `specialization` (enum): "python-coding" | "general-purpose"
- `context_window` (integer): Maximum context length in tokens (e.g., 4096, 16384)
- `status` (enum): "loading" | "ready" | "error"
- `vram_allocated` (integer): GPU memory reserved in bytes
- `backend_url` (string): vLLM instance endpoint (e.g., "http://vllm-coder:8000")
- `created_at` (timestamp): When model loading started
- `ready_at` (timestamp|null): When model became available

**State Transitions**:
```
loading → ready (successful load)
loading → error (load failure due to OOM, missing files, etc.)
```

**Validation Rules**:
- `id` must be unique across all loaded models
- `status` must be "ready" before accepting inference requests
- `context_window` * 0.75 determines safe token limit (FR-013a)

**Relationships**:
- One Model has many Requests (one-to-many)
- One Model serves many Conversations (one-to-many)

---

### 2. Request

Represents a single API call from a client (IDE or WebUI) to generate a response.

**Attributes**:
- `id` (string): UUID for traceability (logged per FR-008)
- `model_id` (string): Target model for this request
- `messages` (array<Message>): Input conversation history
- `streaming` (boolean): Whether response should stream via SSE
- `max_tokens` (integer|null): Maximum tokens to generate
- `temperature` (float): Sampling temperature (0.0-2.0)
- `timestamp` (timestamp): When request was received
- `client_ip` (string): Source IP for logging
- `api_key_hash` (string): Hashed API key for authentication
- `status` (enum): "queued" | "processing" | "completed" | "failed" | "cancelled"
- `queue_position` (integer|null): Position in queue if not processing
- `total_tokens` (integer|null): Combined input + output tokens (computed)

**State Transitions**:
```
queued → processing (slot available in vLLM scheduler)
queued → failed (queue full, returns 503 per FR-009)
processing → completed (successful generation)
processing → failed (error during generation)
processing → cancelled (client disconnected per FR-009a)
```

**Validation Rules**:
- `model_id` must reference a Model with `status="ready"`
- Total input tokens must not exceed model's `context_window * 0.75` (FR-013a)
- Maximum 100 requests in "queued" state per model (FR-009)
- `temperature` must be between 0.0 and 2.0

**Relationships**:
- One Request belongs to one Model (many-to-one)
- One Request is part of one Conversation context (many-to-one, logical)

---

### 3. Conversation

Represents a session between a user and the AI, consisting of multiple message exchanges.

**Attributes**:
- `id` (string): UUID for session identification
- `model_id` (string): Currently selected model
- `messages` (array<Message>): Conversation history (ordered chronologically)
- `current_token_count` (integer): Total tokens across all messages
- `max_token_budget` (integer): `model.context_window * 0.75` (dynamic based on model)
- `created_at` (timestamp): Session start time
- `last_active_at` (timestamp): Last user interaction
- `status` (enum): "active" | "cleared"

**Storage**:
- **WebUI**: Browser sessionStorage (no backend persistence for MVP per assumptions)
- **IDE**: Managed by IDE extension (not stored by our service)

**Token Management Logic**:
```python
def should_truncate(conversation):
    return conversation.current_token_count > conversation.max_token_budget

def truncate_conversation(conversation):
    # Remove oldest messages (keep system message if present)
    while conversation.current_token_count > conversation.max_token_budget:
        if conversation.messages[0].role == "system":
            conversation.messages.pop(1)  # Keep system message
        else:
            conversation.messages.pop(0)
        conversation.current_token_count = sum(msg.tokens for msg in conversation.messages)

    return conversation
```

**Validation Rules**:
- `current_token_count` must not exceed `max_token_budget` (enforced by truncation)
- Warning displayed to user at 60-70% of `max_token_budget` (per edge case spec)
- Messages array must alternate between user/assistant roles (OpenAI API requirement)

**Relationships**:
- One Conversation contains many Messages (one-to-many, composition)
- One Conversation uses one Model at a time (many-to-one)

---

### 4. Message

Represents a single user input or AI response within a conversation.

**Attributes**:
- `id` (string): UUID for message identification
- `role` (enum): "system" | "user" | "assistant"
- `content` (string): Message text
- `tokens` (integer): Token count for this message (computed via tokenizer)
- `timestamp` (timestamp): When message was created
- `model_id` (string|null): Which model generated this (null for user messages)

**Validation Rules**:
- `role` must be one of: "system", "user", "assistant"
- `content` must not be empty string
- `tokens` computed via js-tiktoken (client) or tiktoken (server)
- System messages (if present) must be first in conversation

**Token Counting**:
```typescript
// Client-side (js-tiktoken)
import { encodingForModel } from 'js-tiktoken';
const enc = encodingForModel('gpt-4');
message.tokens = enc.encode(message.content).length;

// Server-side (Python tiktoken)
import tiktoken
enc = tiktoken.encoding_for_model("gpt-4")
message_tokens = len(enc.encode(message["content"]))
```

**Relationships**:
- Many Messages belong to one Conversation (many-to-one)

---

### 5. APIKey

Represents authentication credentials for accessing the service.

**Attributes**:
- `key_value` (string): The actual API key (e.g., "sk-local-abc123")
- `key_hash` (string): SHA-256 hash for secure storage/comparison
- `description` (string): Human-readable label (e.g., "shared-team-key")
- `created_at` (timestamp): Key creation date
- `last_used_at` (timestamp|null): Most recent authentication
- `rotation_date` (timestamp|null): When key should be rotated

**Storage**:
- Single shared key stored in `.env` file (per clarification Q1)
- Format: `API_KEY=sk-local-abc123...`

**Validation Rules**:
- Must start with `sk-` prefix (OpenAI convention)
- Minimum 32 characters length
- Validated on every request via bearer token authentication (FR-003)

**Security Considerations**:
- Never logged in plaintext (only hash logged)
- Transmitted via HTTPS in production (Authorization: Bearer header)
- Rotation capability for security hygiene

---

### 6. QueueEntry (Internal)

Represents a request waiting in the bounded queue.

**Attributes**:
- `request_id` (string): Reference to Request entity
- `model_id` (string): Target model
- `enqueued_at` (timestamp): When added to queue
- `priority` (integer): FIFO order (timestamp-based)
- `client_connection` (WebSocket|HTTP): Connection handle for cancellation detection

**Queue Behavior** (per FR-009):
- Maximum 100 entries per model
- FIFO processing order
- When full: return HTTP 503 with Retry-After header
- Client disconnection: remove from queue (FR-009a)

**Lifecycle**:
```
Request created → QueueEntry added (if no slots available)
→ QueueEntry removed when processing starts
→ or QueueEntry removed if client disconnects
```

---

## Entity Relationship Diagram

```
┌─────────────┐
│   Model     │
│ (2 instances)│
└──────┬──────┘
       │ 1:N
       │
       ▼
┌─────────────┐      ┌──────────────┐
│   Request   │◄─────┤ QueueEntry   │
│             │      │ (max 100/model)
└──────┬──────┘      └──────────────┘
       │ N:1 (logical)
       │
       ▼
┌──────────────┐
│ Conversation │
│ (WebUI only) │
└──────┬───────┘
       │ 1:N
       │
       ▼
┌──────────────┐
│   Message    │
└──────────────┘

┌──────────────┐
│   APIKey     │
│ (singleton)  │
└──────────────┘
```

**Notes**:
- Solid lines = enforced relationships (database/code)
- Dotted lines = logical relationships (context passing)
- Most entities are ephemeral (in-memory, no database)

---

## Data Flow

### Request Processing Flow

```
1. Client sends request → Router
2. Router validates API key (APIKey entity)
3. Router selects backend based on model_id (Model entity)
4. Backend checks Model.status == "ready"
   ├─ If loading: return 503 (FR-029b)
   ├─ If error: return 503 with error message
   └─ If ready: proceed
5. Backend checks queue capacity
   ├─ If slots available: process immediately
   └─ If full: add to QueueEntry (max 100)
6. vLLM processes Request
   ├─ Streaming: yield chunks via SSE
   └─ Non-streaming: return complete response
7. Response returned to client
8. Request logged with full context (FR-008)
```

### Conversation Context Management Flow

```
1. User sends message → WebUI
2. WebUI adds Message to Conversation
3. WebUI calculates current_token_count
4. If current_token_count > max_token_budget (75%):
   ├─ Truncate oldest messages
   ├─ Display warning to user
   └─ Update current_token_count
5. WebUI sends messages array to API
6. API validates token count server-side
7. If valid: process request
8. Assistant response → new Message in Conversation
9. WebUI updates session storage
```

---

## Constraints Summary

| Entity | Constraint | Value | Source |
|--------|-----------|-------|--------|
| Model | Max concurrent | 2 | Constitution Principle II |
| Model | VRAM budget | 96GB total | Hardware |
| Request | Max queue size | 100 per model | FR-009 clarification |
| Request | Queue behavior | FIFO | FR-009 |
| Conversation | Token budget | 75% of context window | FR-013a clarification |
| Conversation | Warning threshold | 60-70% usage | Edge case spec |
| Message | Token counting | js-tiktoken/tiktoken | Research decision |
| APIKey | Format | Single shared key | Clarification Q1 |

---

## Storage Strategy

| Entity | Storage Location | Persistence | Rationale |
|--------|-----------------|-------------|-----------|
| Model | vLLM memory | Duration of service | Loaded at startup |
| Request | Request queue (memory) | Until processed/cancelled | Ephemeral workflow |
| Conversation | sessionStorage (WebUI) | Browser session | MVP assumption |
| Message | Part of Conversation | Browser session | MVP assumption |
| APIKey | `.env` file | File-based | Simple config |
| QueueEntry | Memory (Python deque) | Until processed | Bounded queue |

**No database required for MVP**. Future enhancements (conversation history, multi-user tracking) would introduce persistent storage.

---

## Next Steps

With data model defined, proceed to:
1. Generate API contracts (`contracts/openai-api.yaml`)
2. Create quickstart guide (`quickstart.md`)
3. Update agent context with model decisions
