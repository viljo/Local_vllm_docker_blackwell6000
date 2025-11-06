export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}

export interface Model {
  id: string;
  name: string;
  status: 'loading' | 'ready' | 'error';
}

export interface AppConfig {
  apiBaseUrl: string;
  apiKey: string;
  defaultModel: string;
}
