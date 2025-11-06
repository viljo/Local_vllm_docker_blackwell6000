import { useCallback } from 'react';
import { useChatStore } from '../store/chatStore';
import type { Message } from '../types';
import { generateUUID } from '../utils/uuid';

// Use window.location.hostname for remote access, fallback to env var or localhost
const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  // Use current hostname with API port for remote access
  const hostname = window.location.hostname;
  return `http://${hostname}:8080/v1`;
};

const API_BASE_URL = getApiBaseUrl();
const API_KEY = import.meta.env.VITE_API_KEY || 'sk-local-2ac9387d659f7131f38d83e5f7bee469';

export const useChat = () => {
  const { addMessage, updateLastMessage, setIsLoading, selectedModel } = useChatStore();

  const sendMessage = useCallback(
    async (content: string) => {
      // Add user message
      const userMessage: Message = {
        id: generateUUID(),
        role: 'user',
        content,
        timestamp: Date.now(),
      };
      addMessage(userMessage);

      // Add placeholder for assistant message
      const assistantMessage: Message = {
        id: generateUUID(),
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
      };
      addMessage(assistantMessage);

      setIsLoading(true);

      try {
        // Get conversation history
        const { conversations, currentConversationId } = useChatStore.getState();
        const currentConv = conversations.find((c) => c.id === currentConversationId) || conversations[0];
        const messages = currentConv.messages
          .filter((m) => m.content) // Filter out empty messages
          .map((m) => ({
            role: m.role,
            content: m.content,
          }));

        // Make streaming request using fetch
        const response = await fetch(`${API_BASE_URL}/chat/completions`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${API_KEY}`,
          },
          body: JSON.stringify({
            model: selectedModel,
            messages: messages,
            stream: true,
            max_tokens: 2048,
            temperature: 0.7,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';

        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data === '[DONE]') continue;

                try {
                  const parsed = JSON.parse(data);
                  const delta = parsed.choices?.[0]?.delta?.content || '';
                  if (delta) {
                    fullContent += delta;
                    updateLastMessage(fullContent);
                  }
                } catch (e) {
                  // Skip invalid JSON
                }
              }
            }
          }
        }

        setIsLoading(false);
      } catch (error) {
        console.error('Error sending message:', error);
        updateLastMessage('Error: ' + (error as Error).message + ' - Connection failed. Check console for details.');
        setIsLoading(false);
      }
    },
    [selectedModel, addMessage, updateLastMessage, setIsLoading]
  );

  const fetchModels = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/models`, {
        headers: {
          'Authorization': `Bearer ${API_KEY}`,
        },
      });
      const data = await response.json();
      return data.data || [];
    } catch (error) {
      console.error('Error fetching models:', error);
      return [];
    }
  }, []);

  return { sendMessage, fetchModels };
};
