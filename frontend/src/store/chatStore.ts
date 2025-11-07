import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Message, Conversation, Model } from '../types';
import { generateUUID } from '../utils/uuid';

interface ChatState {
  conversations: Conversation[];
  currentConversationId: string | null;
  models: Model[];
  selectedModel: string;
  isLoading: boolean;

  // Actions
  addConversation: () => void;
  deleteConversation: (id: string) => void;
  setCurrentConversation: (id: string) => void;
  addMessage: (message: Message) => void;
  updateLastMessage: (content: string) => void;
  setModels: (models: Model[]) => void;
  setSelectedModel: (modelId: string) => void;
  setIsLoading: (loading: boolean) => void;
  clearCurrentConversation: () => void;
}

const createNewConversation = (): Conversation => ({
  id: generateUUID(),
  title: 'New Chat',
  messages: [],
  createdAt: Date.now(),
  updatedAt: Date.now(),
});

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      conversations: [createNewConversation()],
      currentConversationId: null,
      models: [],
      selectedModel: '',
      isLoading: false,

      addConversation: () => {
        const newConv = createNewConversation();
        set((state) => ({
          conversations: [...state.conversations, newConv],
          currentConversationId: newConv.id,
        }));
      },

      deleteConversation: (id: string) => {
        set((state) => {
          const filtered = state.conversations.filter((c) => c.id !== id);
          const currentId =
            state.currentConversationId === id
              ? filtered[0]?.id || null
              : state.currentConversationId;
          return {
            conversations: filtered.length > 0 ? filtered : [createNewConversation()],
            currentConversationId: currentId || filtered[0]?.id || null,
          };
        });
      },

      setCurrentConversation: (id: string) => {
        set({ currentConversationId: id });
      },

      addMessage: (message: Message) => {
        set((state) => {
          const convId = state.currentConversationId || state.conversations[0]?.id;
          if (!convId) return state;

          const conversations = state.conversations.map((conv) => {
            if (conv.id === convId) {
              const messages = [...conv.messages, message];
              // Auto-generate title from first user message
              const title =
                messages.length === 1 && message.role === 'user'
                  ? message.content.slice(0, 50) + (message.content.length > 50 ? '...' : '')
                  : conv.title;

              return {
                ...conv,
                messages,
                title,
                updatedAt: Date.now(),
              };
            }
            return conv;
          });

          return { conversations };
        });
      },

      updateLastMessage: (content: string) => {
        set((state) => {
          const convId = state.currentConversationId || state.conversations[0]?.id;
          if (!convId) return state;

          const conversations = state.conversations.map((conv) => {
            if (conv.id === convId) {
              const messages = [...conv.messages];
              if (messages.length > 0) {
                const lastMsg = messages[messages.length - 1];
                messages[messages.length - 1] = {
                  ...lastMsg,
                  content,
                };
              }
              return { ...conv, messages, updatedAt: Date.now() };
            }
            return conv;
          });

          return { conversations };
        });
      },

      setModels: (models: Model[]) => {
        set({ models });
      },

      setSelectedModel: (modelId: string) => {
        set({ selectedModel: modelId });
      },

      setIsLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },

      clearCurrentConversation: () => {
        set((state) => {
          const convId = state.currentConversationId || state.conversations[0]?.id;
          if (!convId) return state;

          const conversations = state.conversations.map((conv) => {
            if (conv.id === convId) {
              return {
                ...conv,
                messages: [],
                title: 'New Chat',
                updatedAt: Date.now(),
              };
            }
            return conv;
          });

          return { conversations };
        });
      },
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({
        conversations: state.conversations,
        currentConversationId: state.currentConversationId,
        selectedModel: state.selectedModel,
      }),
    }
  )
);
