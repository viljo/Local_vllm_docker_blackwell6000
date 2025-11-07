# Smart Model Switching - Feature Specification

## Overview

Implement intelligent model loading/unloading with automatic memory management, real-time progress indication, and user-friendly feedback during model switching operations.

## Core Assumptions

### Fixed Model Set
- **Models are fixed and pre-downloaded** - They do not change, appear, or disappear
- Models cannot be "Not Found" - All configured models are always present on disk
- **UI should NOT show "Stopped" or "Not Found" text** - These states are misleading
- Only show meaningful status: "Running", "Loading", "Failed", etc.
- Empty/stopped models should have no status text (just show model name)

## User Stories

### 1. As a user, I want to see ALL available models in the dropdown
**Current:** Only running models appear in dropdown
**Desired:** All models visible with clear status indicators

**Acceptance Criteria:**
- ✓ Dropdown shows all models (running, stopped, failed)
- ✓ Visual indicators distinguish loaded vs unloaded models
- ✓ Models are grouped or sorted by status
- ✓ No misleading "Not Found" status (models are fixed)

### 2. As a user, I want to switch models seamlessly
**Current:** Must manually start/stop models via Model Manager
**Desired:** Select any model from dropdown, system handles loading

**Acceptance Criteria:**
- ✓ Click any model in dropdown to switch
- ✓ System automatically manages GPU memory
- ✓ Unloads other models if needed
- ✓ Shows progress during switch

### 3. As a user, I want to see loading progress
**Current:** No feedback during model loading (just "Loading..." or error)
**Desired:** Clear progress indication with estimated time

**Acceptance Criteria:**
- ✓ Progress bar or percentage indicator
- ✓ Current stage displayed (e.g., "Loading weights...", "Initializing GPU...")
- ✓ Estimated time remaining
- ✓ Clear error messages if loading fails

### 4. As a user, I want to know when I can't use the chat
**Current:** Error message after sending message to unloaded model
**Desired:** Input locked with explanation during model operations

**Acceptance Criteria:**
- ✓ Input field disabled during model switching
- ✓ Clear message: "Switching to GPT-OSS-120B... (45s remaining)"
- ✓ Cannot send messages until model ready
- ✓ Existing conversation preserved

## Technical Architecture

### Frontend Components

#### 1. Enhanced Model Dropdown
```typescript
interface ModelDropdownItem {
  id: string;
  name: string;
  status: 'loaded' | 'loading' | 'unloading' | 'stopped' | 'failed';
  size_gb: number;
  loadProgress?: number; // 0-100 for loading models
  estimatedTimeRemaining?: number; // seconds
}
```

**UI Elements:**
- Icon/color coding for each status
  - 🟢 Loaded (ready to use)
  - 🔵 Loading... (with spinner)
  - 🟡 Stopped (click to load)
  - 🔴 Failed (error state)
- Size indicator (e.g., "120GB")
- Progress bar for loading models

#### 2. Model Switching Banner
```typescript
interface SwitchingState {
  active: boolean;
  fromModel: string;
  toModel: string;
  stage: 'unloading' | 'loading' | 'initializing';
  progress: number; // 0-100
  eta: number; // seconds
}
```

**UI Elements:**
- Banner above chat: "Switching from DeepSeek to GPT-OSS-120B..."
- Progress bar with percentage
- Estimated time: "~45 seconds remaining"
- Cancel button (optional, advanced)

#### 3. Input Field States
```typescript
type InputState =
  | { type: 'ready' }
  | { type: 'disabled', reason: 'no-model' | 'switching' | 'loading' }
  | { type: 'error', message: string };
```

**UI Behavior:**
- Ready: Normal input, Send button enabled
- Disabled (switching): Grayed out, tooltip explains why
- Disabled (no-model): "Select a model to start chatting"
- Error: Red border, error message below

### Backend API Changes

#### 1. Enhanced Model Status Endpoint
**Endpoint:** `GET /v1/models/status`

**Current Response:**
```json
{
  "models": {
    "gpt-oss-120b": {
      "status": "running",
      "health": "healthy"
    }
  }
}
```

**New Response:**
```json
{
  "models": {
    "gpt-oss-120b": {
      "status": "running",
      "health": "healthy",
      "size_gb": 183,
      "gpu_memory_used_gb": 84,
      "load_progress": 100,
      "estimated_load_time_seconds": 61
    },
    "gpt-oss-20b": {
      "status": "stopped",
      "size_gb": 40,
      "gpu_memory_required_gb": 20,
      "estimated_load_time_seconds": 15
    }
  },
  "gpu": {
    "total_memory_gb": 95.9,
    "used_memory_gb": 84.2,
    "available_memory_gb": 11.7
  }
}
```

#### 2. Smart Model Switch Endpoint
**Endpoint:** `POST /v1/models/switch`

**Request:**
```json
{
  "target_model": "gpt-oss-120b"
}
```

**Response (Streaming SSE):**
```
event: stage
data: {"stage": "checking_memory", "progress": 0}

event: stage
data: {"stage": "unloading_models", "progress": 20, "unloading": ["deepseek-coder-33b-instruct"]}

event: progress
data: {"stage": "unloading", "progress": 40, "model": "deepseek-coder-33b-instruct"}

event: stage
data: {"stage": "loading_target", "progress": 50, "model": "gpt-oss-120b"}

event: progress
data: {"stage": "loading", "progress": 75, "model": "gpt-oss-120b"}

event: complete
data: {"status": "success", "model": "gpt-oss-120b", "total_time_seconds": 65}
```

**Error Response:**
```
event: error
data: {"error": "insufficient_memory", "message": "Cannot free enough memory", "required_gb": 85, "available_gb": 50}
```

### Backend Logic

#### Memory Management Algorithm

```python
def switch_to_model(target_model: str) -> SwitchResult:
    """
    Smart model switching with automatic memory management.

    Algorithm:
    1. Check if target model is already loaded → return immediately
    2. Calculate GPU memory required for target model
    3. Check available GPU memory
    4. If insufficient:
       a. Get list of currently loaded models
       b. Sort by size (largest first)
       c. Unload models one by one until enough memory
       d. If still insufficient → return error
    5. Load target model
    6. Update router to use new model
    """

    # Step 1: Check if already loaded
    if is_model_loaded(target_model):
        return SwitchResult(status="already_loaded", time=0)

    # Step 2: Calculate memory needed
    required_memory = get_model_memory_requirement(target_model)

    # Step 3: Check available memory
    available_memory = get_available_gpu_memory()

    # Step 4: Free memory if needed
    if available_memory < required_memory:
        models_to_unload = select_models_to_unload(
            required_memory - available_memory,
            strategy="largest_first"
        )

        if calculate_freed_memory(models_to_unload) < (required_memory - available_memory):
            return SwitchResult(
                status="error",
                error="insufficient_memory",
                details={
                    "required_gb": required_memory,
                    "available_gb": available_memory,
                    "can_free_gb": calculate_freed_memory(models_to_unload)
                }
            )

        for model in models_to_unload:
            yield ProgressEvent(stage="unloading", model=model, progress=...)
            unload_model(model)

    # Step 5: Load target model
    yield ProgressEvent(stage="loading", model=target_model, progress=0)
    load_model(target_model, progress_callback=lambda p: yield_progress(p))

    return SwitchResult(status="success", model=target_model)


def select_models_to_unload(memory_needed: float, strategy: str) -> List[str]:
    """
    Select which models to unload to free memory.

    Strategies:
    - "largest_first": Unload largest models first (minimize number of operations)
    - "oldest_first": Unload least recently used models first
    - "preserve_favorites": Never unload user-favorited models
    """
    loaded_models = get_loaded_models()

    if strategy == "largest_first":
        # Sort by size descending
        loaded_models.sort(key=lambda m: m.size_gb, reverse=True)

    models_to_unload = []
    freed_memory = 0

    for model in loaded_models:
        if freed_memory >= memory_needed:
            break
        models_to_unload.append(model.name)
        freed_memory += model.gpu_memory_used_gb

    return models_to_unload
```

#### Progress Tracking

```python
class ModelLoadProgress:
    """Track model loading progress across multiple stages."""

    stages = {
        "downloading": (0, 20),      # 0-20% if model not cached
        "loading_weights": (20, 80),  # 20-80% reading from disk
        "initializing_gpu": (80, 95), # 80-95% GPU initialization
        "warming_up": (95, 100)       # 95-100% warmup
    }

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.current_stage = "loading_weights"
        self.stage_progress = 0
        self.start_time = time.time()

    def get_overall_progress(self) -> int:
        """Calculate overall progress (0-100)."""
        stage_min, stage_max = self.stages[self.current_stage]
        stage_range = stage_max - stage_min
        return stage_min + int(stage_range * self.stage_progress / 100)

    def estimate_time_remaining(self) -> int:
        """Estimate seconds remaining based on historical data."""
        elapsed = time.time() - self.start_time
        progress_percent = self.get_overall_progress()

        if progress_percent == 0:
            return self.get_average_load_time(self.model_name)

        total_estimated = elapsed / (progress_percent / 100)
        return int(total_estimated - elapsed)
```

### Frontend Implementation

#### 1. Model Dropdown Component

```typescript
// components/ModelDropdown.tsx
interface ModelDropdownProps {
  models: ModelDropdownItem[];
  selectedModel: string;
  onModelSelect: (modelId: string) => void;
  disabled: boolean;
}

export const ModelDropdown: React.FC<ModelDropdownProps> = ({
  models,
  selectedModel,
  onModelSelect,
  disabled
}) => {
  return (
    <select
      value={selectedModel}
      onChange={(e) => onModelSelect(e.target.value)}
      disabled={disabled}
      className="model-dropdown"
    >
      {models.map(model => (
        <option key={model.id} value={model.id}>
          {getStatusIcon(model.status)} {model.name} ({model.size_gb}GB)
          {model.status === 'loading' && ` - ${model.loadProgress}%`}
        </option>
      ))}
    </select>
  );
};

function getStatusIcon(status: ModelStatus): string {
  switch (status) {
    case 'loaded': return '🟢';
    case 'loading': return '🔵';
    case 'stopped': return '⚪';
    case 'failed': return '🔴';
    default: return '⚫';
  }
}
```

#### 2. Model Switching Banner

```typescript
// components/ModelSwitchingBanner.tsx
interface SwitchingBannerProps {
  switchingState: SwitchingState | null;
}

export const ModelSwitchingBanner: React.FC<SwitchingBannerProps> = ({
  switchingState
}) => {
  if (!switchingState?.active) return null;

  return (
    <div className="switching-banner">
      <div className="switching-info">
        <span className="switching-text">
          Switching to {switchingState.toModel}...
        </span>
        <span className="switching-stage">
          {formatStage(switchingState.stage)}
        </span>
      </div>

      <div className="progress-container">
        <div className="progress-bar" style={{ width: `${switchingState.progress}%` }} />
      </div>

      <div className="switching-eta">
        {switchingState.eta > 0 && `~${switchingState.eta}s remaining`}
      </div>
    </div>
  );
};

function formatStage(stage: string): string {
  switch (stage) {
    case 'unloading': return 'Unloading previous model...';
    case 'loading': return 'Loading model weights...';
    case 'initializing': return 'Initializing GPU...';
    default: return stage;
  }
}
```

#### 3. Chat Hook with Model Switching

```typescript
// hooks/useChat.ts
export const useChat = () => {
  const [switchingState, setSwitchingState] = useState<SwitchingState | null>(null);

  const switchToModel = async (targetModel: string) => {
    setSwitchingState({
      active: true,
      fromModel: selectedModel,
      toModel: targetModel,
      stage: 'loading',
      progress: 0,
      eta: 60
    });

    try {
      // Open SSE connection for progress updates
      const eventSource = new EventSource(
        `${API_BASE_URL}/models/switch?model=${targetModel}`,
        { headers: { 'Authorization': `Bearer ${API_KEY}` } }
      );

      eventSource.addEventListener('progress', (event) => {
        const data = JSON.parse(event.data);
        setSwitchingState(prev => ({
          ...prev!,
          stage: data.stage,
          progress: data.progress,
          eta: data.eta
        }));
      });

      eventSource.addEventListener('complete', (event) => {
        eventSource.close();
        setSwitchingState(null);
        setSelectedModel(targetModel);
      });

      eventSource.addEventListener('error', (event) => {
        eventSource.close();
        const data = JSON.parse(event.data);
        setSwitchingState(null);
        alert(`Failed to switch model: ${data.message}`);
      });

    } catch (error) {
      setSwitchingState(null);
      console.error('Model switch failed:', error);
    }
  };

  return { sendMessage, switchToModel, switchingState };
};
```

## Design Decisions & Trade-offs

### 1. Automatic vs Manual Memory Management

**Option A: Fully Automatic (Recommended)**
- ✅ Best UX - user just clicks, system handles everything
- ✅ Reduces cognitive load
- ⚠️ User may be surprised when models disappear
- ⚠️ Could unload a model user wanted to keep

**Option B: Ask User Confirmation**
```
"Loading GPT-OSS-120B requires 85GB. Currently using 84GB.
Would you like to unload DeepSeek Coder (43GB) to make room?"
[Unload and Switch] [Cancel]
```
- ✅ User stays in control
- ✅ Transparent about what's happening
- ❌ Extra click required
- ❌ Slower workflow

**Recommendation:** Start with Option A, add user preferences later:
```json
{
  "auto_unload": true,
  "preserve_models": ["gpt-oss-120b"], // Never unload these
  "confirm_before_unload": false
}
```

### 2. Unloading Strategy

**Largest First (Recommended)**
- ✅ Minimizes number of operations (unload 1 large vs 3 small)
- ✅ Faster total switch time
- ❌ May unload frequently-used large model

**Least Recently Used (LRU)**
- ✅ Preserves recently-used models
- ✅ Better for workflow with multiple models
- ❌ May need to unload multiple models
- ❌ More complex bookkeeping

**Recommendation:** Implement "largest first" initially, add LRU strategy as option later.

### 3. Progress Indication Granularity

**Option A: Coarse-Grained (3-4 stages)**
```
1. Unloading models... (0-25%)
2. Loading model weights... (25-80%)
3. Initializing GPU... (80-100%)
```
- ✅ Simple to implement
- ✅ Accurate
- ⚠️ May feel slow if stuck at one stage

**Option B: Fine-Grained (10+ substages)**
```
1. Checking GPU memory... (0-5%)
2. Unloading DeepSeek Coder... (5-15%)
3. Freeing GPU memory... (15-20%)
4. Loading weights (batch 1/14)... (20-25%)
...
```
- ✅ Feels faster (constant updates)
- ❌ More complex to track
- ❌ May be inaccurate

**Recommendation:** Use Option A with actual progress tracking from vLLM logs.

### 4. Error Handling

**Scenario: Cannot free enough memory**
```
User has:
- GPT-OSS-120B loaded (85GB)
- 95GB total GPU

User tries to load:
- Another GPT-OSS-120B instance (needs 85GB)
```

**Options:**
1. Show error: "Insufficient GPU memory. Please unload GPT-OSS-120B first."
2. Auto-unload everything and try
3. Suggest smaller model: "Not enough memory. Try GPT-OSS-20B instead?"

**Recommendation:** Option 1 with helpful message and link to Model Manager.

### 5. Concurrent Requests

**Problem:** User rapidly clicks different models while switching

**Solution:** Queue or cancel?
- **Queue:** Process switches in order (may take minutes)
- **Cancel:** Cancel current switch, start new one

**Recommendation:** Cancel current, start new (with confirmation if >50% complete)

## Implementation Phases

### Phase 1: Foundation (Week 1)
- ✓ Enhanced `/v1/models/status` endpoint with memory info
- ✓ Basic model switching endpoint (no auto-unload yet)
- ✓ Frontend: Show all models in dropdown with status icons
- ✓ Frontend: Disable input during loading

### Phase 2: Smart Switching (Week 2)
- ✓ Implement memory checking logic
- ✓ Implement "largest first" unloading strategy
- ✓ SSE progress streaming
- ✓ Frontend: Progress banner with percentage

### Phase 3: Polish (Week 3)
- ✓ Accurate progress tracking from vLLM
- ✓ Error handling and user feedback
- ✓ Estimated time remaining
- ✓ Cancel operation support

### Phase 4: Advanced (Future)
- User preferences (auto-unload, preserve models)
- LRU unloading strategy
- Model favorites/pinning
- Preload models in background

## Edge Cases

### 1. Multiple Browser Tabs
- User has 2 tabs open
- Tab A switches to Model X
- Tab B doesn't know about switch

**Solution:** WebSocket or polling to sync state across tabs

### 2. Model Fails to Load
- Started unloading other models
- Target model fails to load
- Now user has NO models loaded

**Solution:** Keep at least one model loaded at all times, or auto-rollback

### 3. Container Crash During Switch
- Mid-way through unloading
- Docker container crashes
- System state unknown

**Solution:** Health check and recovery endpoint to detect and fix

### 4. Extremely Slow Disk
- Model taking 5+ minutes to load
- User thinks it's frozen

**Solution:**
- Show actual bytes loaded (e.g., "45GB / 183GB")
- Add "this may take a while" message
- Allow cancellation

## Security Considerations

1. **Rate Limiting:** Prevent rapid model switching DoS
2. **Authentication:** Require API key for model switching
3. **Resource Limits:** Maximum N switches per minute
4. **Audit Logging:** Log all model operations

## Performance Considerations

1. **Model Switch Time:** Target <90 seconds for largest models
2. **API Response Time:** Status endpoint <100ms
3. **Frontend Polling:** Poll status every 2-3 seconds during switch
4. **Memory Overhead:** Switching should not require >10% extra RAM

## Testing Strategy

### Unit Tests
- Memory calculation logic
- Model selection algorithm
- Progress tracking accuracy

### Integration Tests
- Full switch workflow
- Error scenarios (OOM, timeout, crash)
- Concurrent requests

### E2E Tests
- User clicks model → switch completes
- Progress updates appear
- Input locked during switch
- Error messages shown

## Success Metrics

- ✅ 95%+ successful model switches
- ✅ <2% user-reported confusion
- ✅ Average switch time <90s for 120B model
- ✅ Zero data loss during switches
- ✅ 100% state synchronization across tabs

## Open Questions for Discussion

1. **Should we allow multiple models loaded simultaneously (if memory permits)?**
   - Pro: Faster switching between cached models
   - Con: Uses more GPU memory, fewer KV cache

2. **Should we show estimated costs/time before switching?**
   ```
   Switching to GPT-OSS-120B will:
   - Take ~60 seconds
   - Use 85GB GPU memory
   - Unload DeepSeek Coder
   Proceed? [Yes] [No]
   ```

3. **Should we prefetch/warmup models in background?**
   - When user opens dropdown, start loading popular models
   - Pro: Instant switching for common models
   - Con: Wastes GPU memory speculatively

4. **How to handle model updates/new versions?**
   - Auto-reload when new version detected?
   - Show "Update Available" badge?

5. **Should we persist last-used model across sessions?**
   - localStorage: Remember user's last model
   - Auto-load it on page load
