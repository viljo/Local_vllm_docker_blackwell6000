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

  const { sendMessage, fetchModels, getModelsStatus, startModel, stopModel } = useChat();
  const [input, setInput] = useState('');
  const [modelStatus, setModelStatus] = useState<Record<string, any>>({});
  const [showModelManager, setShowModelManager] = useState(false);
  const [unloadingModels, setUnloadingModels] = useState<Set<string>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const currentConv =
    conversations.find((c) => c.id === currentConversationId) || conversations[0];

  // Fetch models and status on mount
  useEffect(() => {
    const fetchData = async () => {
      const [fetchedModels, status] = await Promise.all([
        fetchModels(),
        getModelsStatus(),
      ]);

      if (fetchedModels.length > 0) {
        setModels(
          fetchedModels.map((m: any) => ({
            id: m.id,
            name: m.id,
            status: m.status || 'ready',
          }))
        );
      }
      setModelStatus(status);
    };

    fetchData();
    // Refresh status every 30 seconds
    const interval = setInterval(async () => {
      const status = await getModelsStatus();
      setModelStatus(status);
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchModels, getModelsStatus, setModels]);

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

  const handleStartModel = async (modelName: string) => {
    try {
      await startModel(modelName);
      // Refresh status after a short delay
      setTimeout(async () => {
        const status = await getModelsStatus();
        setModelStatus(status);
      }, 2000);
    } catch (error) {
      console.error('Failed to start model:', error);
    }
  };

  const handleStopModel = async (modelName: string) => {
    try {
      // Immediately mark as unloading
      setUnloadingModels(prev => new Set(prev).add(modelName));

      await stopModel(modelName);

      // Refresh status and clear unloading state
      const status = await getModelsStatus();
      setModelStatus(status);
      setUnloadingModels(prev => {
        const next = new Set(prev);
        next.delete(modelName);
        return next;
      });
    } catch (error) {
      console.error('Failed to stop model:', error);
      // Clear unloading state on error
      setUnloadingModels(prev => {
        const next = new Set(prev);
        next.delete(modelName);
        return next;
      });
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

          <button
            className="model-manager-btn"
            onClick={() => setShowModelManager(!showModelManager)}
          >
            Model Manager {showModelManager ? '▼' : '▶'}
          </button>
        </div>

        {/* Model Manager Panel */}
        {showModelManager && (
          <div className="model-manager">
            <h3>Model Management</h3>
            <div className="model-list">
              {Object.entries(modelStatus).map(([modelName, status]: [string, any]) => {
                const getStatusDisplay = () => {
                  // Check client-side unloading state first
                  if (unloadingModels.has(modelName)) {
                    return { icon: '◑', text: 'Unloading model', color: 'unloading' };
                  }

                  switch (status.status) {
                    case 'running':
                      return { icon: '●', text: 'Running', color: 'running' };
                    case 'loading':
                      return { icon: '◐', text: 'Loading into GPU-mem', color: 'loading' };
                    case 'unloading':
                      return { icon: '◑', text: 'Unloading model', color: 'unloading' };
                    case 'insufficient_gpu_ram':
                      return { icon: '⚠', text: 'Insufficient free GPU-ram', color: 'insufficient_gpu_ram' };
                    case 'failed':
                      return { icon: '✕', text: 'Failed', color: 'failed' };
                    case 'exited':
                      return { icon: '○', text: 'Stopped', color: 'stopped' };
                    default:
                      return { icon: '○', text: 'Not Found', color: 'not_found' };
                  }
                };

                const statusDisplay = getStatusDisplay();
                const isActionDisabled = status.status === 'loading' || status.status === 'unloading' || unloadingModels.has(modelName);

                return (
                  <div key={modelName} className="model-item">
                    <div className="model-info">
                      <div className="model-header">
                        <span className="model-name">{modelName}</span>
                        <span className={`model-status status-${statusDisplay.color}`}>
                          {statusDisplay.icon} {statusDisplay.text}
                        </span>
                      </div>
                      {status.description && (
                        <span className="model-description">{status.description}</span>
                      )}
                      <div className="model-meta">
                        {status.size_gb && (
                          <span className="model-size">Size: {status.size_gb} GB</span>
                        )}
                        {status.downloaded !== undefined && (
                          <span className={`download-status ${status.downloaded ? 'downloaded' : 'not-downloaded'}`}>
                            {status.downloaded ? (
                              <>
                                ✓ Downloaded
                                {status.downloaded_size && ` (${status.downloaded_size})`}
                              </>
                            ) : (
                              '⚠ Not Downloaded'
                            )}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="model-actions">
                      {status.status === 'running' || status.status === 'loading' ? (
                        <button
                          className="stop-model-btn"
                          onClick={() => handleStopModel(modelName)}
                          disabled={isActionDisabled}
                        >
                          Stop
                        </button>
                      ) : (
                        <button
                          className="start-model-btn"
                          onClick={() => handleStartModel(modelName)}
                          disabled={isActionDisabled || !status.downloaded}
                          title={!status.downloaded ? 'Model not downloaded' : ''}
                        >
                          Start
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

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
