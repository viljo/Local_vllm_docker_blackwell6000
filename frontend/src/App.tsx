import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useChatStore } from './store/chatStore';
import { useChat } from './hooks/useChat';
import './App.css';

function App() {
  const {
    conversations,
    currentConversationId,
    selectedModel,
    isLoading,
    addConversation,
    deleteConversation,
    setCurrentConversation,
    setModels,
    setSelectedModel,
    clearCurrentConversation,
  } = useChatStore();

  const { sendMessage, fetchModels, getModelsStatus, stopModel, switchModel } = useChat();
  const [input, setInput] = useState('');
  const [modelStatus, setModelStatus] = useState<Record<string, any>>({});
  const [gpuInfo, setGpuInfo] = useState<any>({});
  const [showModelManager, setShowModelManager] = useState(false);
  const [unloadingModels, setUnloadingModels] = useState<Set<string>>(new Set());
  const [isSwitchingModel, setIsSwitchingModel] = useState(false);
  const [switchingInfo, setSwitchingInfo] = useState<any>(null);
  const [showApiInfo, setShowApiInfo] = useState(false);
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
        const modelList = fetchedModels.map((m: any) => ({
          id: m.id,
          name: m.id,
          status: m.status || 'ready',
        }));
        setModels(modelList);

        // Auto-select first model if none selected
        if (!selectedModel && modelList.length > 0) {
          setSelectedModel(modelList[0].id);
        }
      }
      setModelStatus(status.models);
      setGpuInfo(status.gpu);
    };

    fetchData();

    // Refresh models and status every 30 seconds
    const modelInterval = setInterval(async () => {
      const [fetchedModels, status] = await Promise.all([
        fetchModels(),
        getModelsStatus(),
      ]);

      if (fetchedModels.length > 0) {
        const modelList = fetchedModels.map((m: any) => ({
          id: m.id,
          name: m.id,
          status: m.status || 'ready',
        }));
        setModels(modelList);

        // Auto-select first model if currently selected model is not in the list
        const selectedExists = modelList.some((m: any) => m.id === selectedModel);
        if (!selectedExists && modelList.length > 0) {
          setSelectedModel(modelList[0].id);
        }
      }
      setModelStatus(status.models);
      setGpuInfo(status.gpu);
    }, 30000);

    // Refresh GPU stats every 2 seconds for live updates
    const gpuInterval = setInterval(async () => {
      const status = await getModelsStatus();
      setGpuInfo(status.gpu);
      setModelStatus(status.models);
    }, 2000);

    return () => {
      clearInterval(modelInterval);
      clearInterval(gpuInterval);
    };
  }, [fetchModels, getModelsStatus, setModels, selectedModel, setSelectedModel]);

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
      // Use smart switching logic - same as dropdown
      setIsSwitchingModel(true);
      setSwitchingInfo({ targetModel: modelName, unloadedModels: [] });

      const result = await switchModel(modelName);

      if (result.status === 'success' || result.status === 'already_loaded' || result.status === 'timeout') {
        setSwitchingInfo({
          targetModel: modelName,
          unloadedModels: result.unloaded_models || [],
          estimatedLoadTime: result.estimated_load_time_seconds || 60,
        });

        // Show a note if request timed out
        if (result.status === 'timeout') {
          console.warn('Start request timed out, but backend is still processing. Polling for completion...');
        }

        // Poll status until model is ready
        const pollInterval = setInterval(async () => {
          const status = await getModelsStatus();
          setModelStatus(status.models);
          setGpuInfo(status.gpu);

          // Check if target model is running and healthy
          if (status.models[modelName]?.status === 'running' && status.models[modelName]?.health === 'healthy') {
            clearInterval(pollInterval);
            setIsSwitchingModel(false);
            setSwitchingInfo(null);
            setSelectedModel(modelName);

            // Refresh models list
            const fetchedModels = await fetchModels();
            if (fetchedModels.length > 0) {
              setModels(
                fetchedModels.map((m: any) => ({
                  id: m.id,
                  name: m.id,
                  status: m.status || 'ready',
                }))
              );
            }
          }
        }, 3000); // Poll every 3 seconds

        // Timeout after 2 minutes
        setTimeout(() => {
          clearInterval(pollInterval);
          if (isSwitchingModel) {
            setIsSwitchingModel(false);
            setSwitchingInfo(null);
            alert('Model starting timed out. Please check Model Manager for status.');
          }
        }, 120000);
      } else {
        throw new Error(result.message || 'Failed to start model');
      }
    } catch (error) {
      console.error('Model start failed:', error);
      setIsSwitchingModel(false);
      setSwitchingInfo(null);
      alert(`Failed to start ${modelName}: ${(error as Error).message}`);
    }
  };

  const handleStopModel = async (modelName: string) => {
    try {
      // Immediately mark as unloading
      setUnloadingModels(prev => new Set(prev).add(modelName));

      await stopModel(modelName);

      // Refresh models and status, then clear unloading state
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
      setModelStatus(status.models);
      setGpuInfo(status.gpu);
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

  const handleModelChange = async (newModel: string) => {
    // Set switching state immediately to lock UI
    setIsSwitchingModel(true);

    // Check if model is already running and healthy
    const status = modelStatus[newModel];
    if (status?.status === 'running' && status?.health === 'healthy') {
      // Model is ready, just switch to it
      setSelectedModel(newModel);
      setIsSwitchingModel(false);
      return;
    }

    // Model needs to be switched, show switching UI
    try {
      setSwitchingInfo({ targetModel: newModel, unloadedModels: [] });

      const result = await switchModel(newModel);

      // Handle success, already_loaded, or timeout (timeout means backend is still processing)
      if (result.status === 'success' || result.status === 'already_loaded' || result.status === 'timeout') {
        setSwitchingInfo({
          targetModel: newModel,
          unloadedModels: result.unloaded_models || [],
          estimatedLoadTime: result.estimated_load_time_seconds || 60, // Default to 60s for timeout
        });

        // Show a note if request timed out
        if (result.status === 'timeout') {
          console.warn('Switch request timed out, but backend is still processing. Polling for completion...');
        }

        // Poll status until model is ready
        const pollInterval = setInterval(async () => {
          const status = await getModelsStatus();
          setModelStatus(status.models);
          setGpuInfo(status.gpu);

          // Check if target model is running and healthy
          if (status.models[newModel]?.status === 'running' && status.models[newModel]?.health === 'healthy') {
            clearInterval(pollInterval);
            setIsSwitchingModel(false);
            setSwitchingInfo(null);
            setSelectedModel(newModel);

            // Refresh models list
            const fetchedModels = await fetchModels();
            if (fetchedModels.length > 0) {
              setModels(
                fetchedModels.map((m: any) => ({
                  id: m.id,
                  name: m.id,
                  status: m.status || 'ready',
                }))
              );
            }
          }
        }, 3000); // Poll every 3 seconds

        // Timeout after 2 minutes
        setTimeout(() => {
          clearInterval(pollInterval);
          if (isSwitchingModel) {
            setIsSwitchingModel(false);
            setSwitchingInfo(null);
            alert('Model switching timed out. Please check Model Manager for status.');
          }
        }, 120000);
      } else {
        throw new Error(result.message || 'Failed to switch model');
      }
    } catch (error) {
      console.error('Model switching failed:', error);
      setIsSwitchingModel(false);
      setSwitchingInfo(null);
      alert(`Failed to switch to ${newModel}: ${(error as Error).message}`);
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
            onChange={(e) => handleModelChange(e.target.value)}
            disabled={isSwitchingModel}
          >
            {Object.keys(modelStatus).length > 0 ? (
              <>
                {/* Running/Ready Models */}
                <optgroup label="━━━ Ready ━━━">
                  {Object.entries(modelStatus)
                    .filter(([_, status]: [string, any]) =>
                      status.status === 'running' && status.health === 'healthy'
                    )
                    .map(([modelName, status]: [string, any]) => (
                      <option key={modelName} value={modelName}>
                        ● {modelName} ({status.gpu_memory_gb}GB VRAM)
                      </option>
                    ))}
                </optgroup>

                {/* Available/Stopped Models */}
                <optgroup label="━━━ Available ━━━">
                  {Object.entries(modelStatus)
                    .filter(([_, status]: [string, any]) =>
                      (status.status !== 'running' || status.health !== 'healthy') &&
                      status.status !== 'not_found'
                    )
                    .map(([modelName, status]: [string, any]) => {
                      const statusText = status.status === 'loading' ? 'Loading' :
                                        status.status === 'requires_unload' ? 'Requires unload' :
                                        status.status === 'insufficient_gpu_ram' ? 'Too large' :
                                        status.status === 'failed' ? 'Failed' : 'Stopped';
                      return (
                        <option key={modelName} value={modelName}>
                          ○ {modelName} ({status.gpu_memory_gb}GB VRAM) - {statusText}
                        </option>
                      );
                    })}
                </optgroup>
              </>
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

          <button
            className="api-info-btn"
            onClick={() => setShowApiInfo(!showApiInfo)}
          >
            API Info {showApiInfo ? '▼' : '▶'}
          </button>
        </div>

        {/* Model Manager Panel */}
        {showModelManager && (
          <div className="model-manager">
            <h3>
              Model Management
              {gpuInfo.available_gb !== undefined && (
                <span className="gpu-stats">
                  {' - '}{gpuInfo.available_gb}GB VideoRam free ({gpuInfo.used_gb}GB used)
                </span>
              )}
            </h3>
            <div className="model-list">
              {Object.entries(modelStatus)
                .filter(([_, status]: [string, any]) => status.status !== 'not_found')
                .map(([modelName, status]: [string, any]) => {
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
                    case 'requires_unload':
                      return { icon: '⚠', text: 'Warning - Causes unload of current models', color: 'requires_unload' };
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
                const isActionDisabled = status.status === 'loading' || unloadingModels.has(modelName) || isSwitchingModel;

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
                        {status.gpu_memory_gb && (
                          <span className="model-size">VRAM: {status.gpu_memory_gb} GB</span>
                        )}
                        {status.downloaded_size && (
                          <span className="model-size">Disk: {status.downloaded_size}</span>
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
                          disabled={isActionDisabled}
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

        {/* API Info Panel */}
        {showApiInfo && (
          <div className="api-info-panel">
            <h3>API Connection Information</h3>
            <div className="api-info-content">
              <div className="api-info-item">
                <label className="api-info-label">Base URL:</label>
                <div className="api-info-value">
                  <code>{`http://${window.location.hostname}:8080/v1`}</code>
                  <button
                    className="copy-btn"
                    onClick={() => {
                      navigator.clipboard.writeText(`http://${window.location.hostname}:8080/v1`);
                      alert('URL copied to clipboard!');
                    }}
                  >
                    Copy
                  </button>
                </div>
              </div>
              <div className="api-info-item">
                <label className="api-info-label">API Key:</label>
                <div className="api-info-value">
                  <code>sk-local-2ac9387d659f7131f38d83e5f7bee469</code>
                  <button
                    className="copy-btn"
                    onClick={() => {
                      navigator.clipboard.writeText('sk-local-2ac9387d659f7131f38d83e5f7bee469');
                      alert('API key copied to clipboard!');
                    }}
                  >
                    Copy
                  </button>
                </div>
              </div>
              <div className="api-info-note">
                Use these credentials to connect external tools like Continue, Cursor, or any OpenAI-compatible client.
              </div>
            </div>
          </div>
        )}

        {/* Model Switching Banner */}
        {isSwitchingModel && switchingInfo && (
          <div className="model-switching-banner">
            <div className="switching-content">
              <div className="switching-header">
                <span className="switching-icon">⚙️</span>
                <span className="switching-text">
                  Switching to {switchingInfo.targetModel}...
                </span>
              </div>
              {switchingInfo.unloadedModels && switchingInfo.unloadedModels.length > 0 && (
                <div className="switching-details">
                  Unloaded: {switchingInfo.unloadedModels.join(', ')}
                </div>
              )}
              {switchingInfo.estimatedLoadTime && (
                <div className="switching-details">
                  Estimated time: ~{switchingInfo.estimatedLoadTime}s
                </div>
              )}
              <div className="switching-progress">
                <div className="progress-bar">
                  <div className="progress-fill"></div>
                </div>
              </div>
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
              placeholder={isSwitchingModel ? "Model is loading, please wait..." : "Send a message..."}
              disabled={isLoading || isSwitchingModel}
            />
            <button className="send-btn" type="submit" disabled={isLoading || isSwitchingModel || !input.trim()}>
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default App;
