import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useChatStore } from './store/chatStore';
import { useChat } from './hooks/useChat';
import './App.css';

function App() {
  const {
    conversations,
    currentConversationId,
    models,
    selectedModel,
    isLoading,
    addConversation,
    deleteConversation,
    setCurrentConversation,
    setModels,
    setSelectedModel,
    clearCurrentConversation,
  } = useChatStore();

  const { sendMessage, fetchModels } = useChat();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const currentConv =
    conversations.find((c) => c.id === currentConversationId) || conversations[0];

  // Fetch models on mount
  useEffect(() => {
    fetchModels().then((fetchedModels) => {
      if (fetchedModels.length > 0) {
        setModels(
          fetchedModels.map((m: any) => ({
            id: m.id,
            name: m.id,
            status: m.status || 'ready',
          }))
        );
      }
    });
  }, [fetchModels, setModels]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentConv?.messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const message = input.trim();
    setInput('');
    await sendMessage(message);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="app">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={addConversation}>
            + New Chat
          </button>
        </div>

        <div className="conversation-list">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${conv.id === currentConv?.id ? 'active' : ''}`}
              onClick={() => setCurrentConversation(conv.id)}
            >
              <span className="conversation-title">{conv.title}</span>
              {conversations.length > 1 && (
                <button
                  className="delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteConversation(conv.id);
                  }}
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        <div className="header">
          <select
            className="model-selector"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
          >
            {models.length > 0 ? (
              models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name} {model.status !== 'ready' ? `(${model.status})` : ''}
                </option>
              ))
            ) : (
              <>
                <option value="deepseek-coder-33b-instruct">
                  DeepSeek Coder 33B (Python)
                </option>
                <option value="mistral-7b-v0.1">Mistral 7B (General)</option>
              </>
            )}
          </select>

          <button className="clear-btn" onClick={clearCurrentConversation}>
            Clear Chat
          </button>
        </div>

        <div className="messages-container">
          {currentConv?.messages.length === 0 ? (
            <div className="empty-state">
              <h2>Local LLM Chat</h2>
              <p>
                Start a conversation with your local AI models. Choose between Python-focused
                DeepSeek Coder or general-purpose Mistral models.
              </p>
              <p style={{ marginTop: '20px' }}>
                <a
                  href="/test.html"
                  target="_blank"
                  style={{
                    color: '#10a37f',
                    textDecoration: 'none',
                    padding: '10px 20px',
                    border: '1px solid #10a37f',
                    borderRadius: '6px',
                    display: 'inline-block'
                  }}
                >
                  🔧 API Connection Test Page
                </a>
              </p>
            </div>
          ) : (
            currentConv?.messages.map((message) => (
              <div key={message.id} className={`message ${message.role}`}>
                <div>
                  <div className="message-role">
                    {message.role === 'user' ? 'You' : 'Assistant'}
                  </div>
                  <div className="message-content">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                </div>
              </div>
            ))
          )}

          {isLoading && (
            <div className="loading">
              <div className="loading-dot"></div>
              <div className="loading-dot"></div>
              <div className="loading-dot"></div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <form onSubmit={handleSubmit} className="input-wrapper">
            <textarea
              className="message-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Send a message..."
              disabled={isLoading}
            />
            <button className="send-btn" type="submit" disabled={isLoading || !input.trim()}>
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default App;
