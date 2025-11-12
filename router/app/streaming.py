"""
Streaming handlers for tool calling support
Handles buffered streaming with tool detection and usage statistics
"""
import json
import logging
import time
from typing import AsyncIterator, Optional, Dict, Any, List

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logging.warning("tiktoken not available - token counting will be approximate")

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text (fallback when tiktoken unavailable).

    Uses rough approximation: ~4 characters per token for English text.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    return max(1, len(text) // 4)


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in text using tiktoken if available, otherwise estimate.

    Args:
        text: Text to count tokens for
        model: Model name for tokenizer selection

    Returns:
        Token count
    """
    if not TIKTOKEN_AVAILABLE:
        return estimate_tokens(text)

    try:
        # Use cl100k_base encoding (GPT-4, GPT-3.5-turbo)
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"Token counting failed: {e}, falling back to estimation")
        return estimate_tokens(text)


def create_usage_chunk(
    prompt_tokens: int,
    completion_tokens: int,
    chunk_id: str,
    model: str
) -> str:
    """
    Create final streaming chunk with usage statistics.

    Args:
        prompt_tokens: Number of tokens in prompt
        completion_tokens: Number of tokens in completion
        chunk_id: Chunk ID from response
        model: Model name

    Returns:
        Formatted SSE chunk with usage data
    """
    usage_data = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    }

    return f"data: {json.dumps(usage_data)}\n\n"


async def stream_with_tool_detection(
    backend_stream: AsyncIterator[str],
    request,
    model: str
) -> AsyncIterator[str]:
    """
    Enhanced streaming that buffers output to detect tool calls and add usage stats.

    This function:
    1. Collects all streaming chunks
    2. Detects tool calls in the complete response
    3. Modifies chunks to inject tool_calls if detected
    4. Adds usage statistics chunk if requested

    Args:
        backend_stream: Async iterator of backend response chunks
        request: Original request object
        model: Model name for token counting

    Yields:
        Modified streaming chunks as strings
    """
    from .tool_parsing import extract_tool_calls_from_text

    chunks = []
    full_content = ""
    chunk_id = None
    prompt_text = ""

    # Calculate prompt tokens if usage requested
    if request.stream_options and request.stream_options.get("include_usage"):
        # Construct prompt from messages
        for msg in request.messages:
            role = msg.role if hasattr(msg, 'role') else msg.get('role', '')
            content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
            if content:
                prompt_text += f"{role}: {content}\n"

        # Add tool definitions to prompt tokens
        if request.tools:
            from .transformations import tools_to_system_prompt
            tool_prompt = tools_to_system_prompt(request.tools)
            prompt_text += tool_prompt

    # Collect all chunks and build full content
    logger.debug("Buffering streaming chunks for tool detection")
    async for chunk_str in backend_stream:
        chunks.append(chunk_str)

        # Parse chunk to extract content
        if chunk_str.startswith('data: '):
            data_str = chunk_str[6:].strip()

            if data_str == '[DONE]':
                continue

            try:
                chunk_data = json.loads(data_str)

                # Extract chunk ID
                if not chunk_id and 'id' in chunk_data:
                    chunk_id = chunk_data['id']

                # Build full content from deltas
                if 'choices' in chunk_data and chunk_data['choices']:
                    delta = chunk_data['choices'][0].get('delta', {})
                    content = delta.get('content', '')
                    if content:
                        full_content += content

            except json.JSONDecodeError:
                logger.debug(f"Could not parse chunk: {data_str[:100]}")
                continue

    logger.debug(f"Collected {len(chunks)} chunks, content length: {len(full_content)}")

    # Detect tool calls in complete content
    tool_calls = None
    if request.tools and full_content:
        tool_calls = extract_tool_calls_from_text(full_content)
        if tool_calls:
            logger.info(f"Detected {len(tool_calls)} tool call(s) in streaming response")

    # Stream chunks with modifications
    for i, chunk_str in enumerate(chunks):
        if not chunk_str.startswith('data: '):
            yield chunk_str
            continue

        data_str = chunk_str[6:].strip()

        if data_str == '[DONE]':
            # Before [DONE], inject usage chunk if requested
            if request.stream_options and request.stream_options.get("include_usage"):
                prompt_tokens = count_tokens(prompt_text, model)
                completion_tokens = count_tokens(full_content, model)

                usage_chunk = create_usage_chunk(
                    prompt_tokens,
                    completion_tokens,
                    chunk_id or "chatcmpl-unknown",
                    model
                )
                yield usage_chunk

            yield chunk_str
            continue

        try:
            chunk_data = json.loads(data_str)

            # Check if this is the last chunk with finish_reason
            if 'choices' in chunk_data and chunk_data['choices']:
                choice = chunk_data['choices'][0]

                # Inject tool_calls in the final chunk
                if tool_calls and choice.get('finish_reason'):
                    # Modify delta to include tool_calls
                    if 'delta' not in choice:
                        choice['delta'] = {}

                    choice['delta']['tool_calls'] = tool_calls
                    choice['finish_reason'] = 'tool_calls'

                    # Update chunk data
                    chunk_data['choices'][0] = choice
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                    continue

            # Yield unmodified chunk
            yield chunk_str

        except json.JSONDecodeError:
            # If we can't parse, just pass through
            yield chunk_str


async def simple_stream_passthrough(
    backend_stream: AsyncIterator[str]
) -> AsyncIterator[str]:
    """
    Simple passthrough for streaming when no tool processing needed.

    Args:
        backend_stream: Async iterator of backend response chunks

    Yields:
        Chunks as-is from backend
    """
    async for chunk in backend_stream:
        yield chunk
