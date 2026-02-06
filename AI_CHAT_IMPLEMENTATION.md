# AI Chat Interface - Implementation Guide

## ✅ Completed

### Backend (Already Exists)
- `backend/app/api/v1/endpoints/chat.py` - REST API endpoints for chat
- `backend/app/services/ai_chat_service.py` - Chat service with OpenRouter integration
- Database models for Conversation and Message
- System prompt for AI image manipulation

### Frontend (Just Created)
- `frontend/src/services/chatService.js` - API client for chat endpoints
- `frontend/src/components/ChatInterface.vue` - Full chat UI component with:
  - Message list with user/assistant messages
  - Input field with send button
  - Welcome message with examples
  - Loading/typing indicator
  - Operation tags display
  - Connection warning
  - Error handling
  - Auto-scroll to bottom
  - Mobile responsive design

## 🔴 Remaining Implementation Steps

### Step 1: Add Chat Button to ImageCard.vue

**Location:** After the "Remove Background" button (around line 127)

```vue
<button 
  @click="openChatInterface" 
  class="btn-icon btn-ai"
  :disabled="isProcessing"
  :title="'AI Chat - Ask AI to modify image'"
>
  <span class="icon">💬</span>
  <span class="tooltip">AI Chat</span>
</button>
```

**Add to script section (around line 295):**

```javascript
// Add new props
const props = defineProps({
  image: {
    type: Object,
    required: true
  },
  presets: {
    type: Array,
    default: () => []
  },
  sessionId: {
    type: String,
    required: true
  },
  selectedModel: {
    type: String,
    default: null
  },
  isOpenRouterConnected: {
    type: Boolean,
    default: false
  }
});

// Add new refs
const showChatInterface = ref(false);

// Add method
const openChatInterface = () => {
  showChatInterface.value = true;
};

const closeChatInterface = () => {
  showChatInterface.value = false;
};

const handleOperationsApplied = (operations) => {
  // Operations were applied by backend, reload image
  console.log('Operations applied:', operations);
  imageRefreshKey.value = Date.now(); // Force image refresh
};
```

**Add to template (at end, before closing div):**

```vue
<!-- Chat Interface Modal -->
<ChatInterface
  v-if="showChatInterface"
  :image="image"
  :sessionId="sessionId"
  :selectedModel="selectedModel"
  :isConnected="isOpenRouterConnected"
  @close="closeChatInterface"
  @operationsApplied="handleOperationsApplied"
/>
```

**Add import at top of script:**

```javascript
import ChatInterface from './ChatInterface.vue';
```

### Step 2: Update App.vue to Pass Props to ImageCard

**Location:** Find where ImageCard is used (search for `<ImageCard`)

**Add props to ImageCard component:**

```vue
<ImageCard
  v-for="image in imageStore.images"
  :key="image.id"
  :image="image"
  :presets="presets"
  :sessionId="sessionId"
  :selectedModel="selectedModel"
  :isOpenRouterConnected="openRouterConnected"
  @image-click="handleImageClick"
  @edit-click="handleEditClick"
/>
```

### Step 3: Initialize Chat Service in App.vue

**Location:** In the `initializeApp()` function (around line 925)

**Add after setting session ID for openRouterService:**

```javascript
// Set session ID in chat service
import { chatService } from './services/chatService';

// In initializeApp():
if (sessionId.value) {
  openRouterService.setSessionId(sessionId.value);
  chatService.setSessionId(sessionId.value); // ADD THIS LINE
}
```

### Step 4: Test the Chat Interface

1. **Start servers:**
   ```bash
   # Backend
   cd backend
   ./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
   
   # Frontend
   cd frontend
   npm run dev
   ```

2. **Test workflow:**
   - Upload an image
   - Connect to OpenRouter (AI Settings)
   - Select an AI model
   - Click the AI Chat button (💬) on any image card
   - Type a message like "Make it brighter"
   - Verify AI responds and operations are applied

### Step 5: Backend API Key Integration

The chat currently expects the API key to be available. There are two options:

**Option A: Use session-based encrypted key (Recommended)**

Update `chatService.js` to NOT send api_key in request - the backend should fetch it from the `openrouter_keys` table using the session_id.

**Update backend:** `backend/app/services/ai_chat_service.py` (around line 86)

```python
# Instead of requiring API key in request, fetch from database
from app.services.openrouter_oauth_service import OpenRouterOAuthService

async def send_message(self, request: ChatRequest) -> ChatResponse:
    # Fetch encrypted API key from database using session_id
    oauth_service = OpenRouterOAuthService(self.db)
    key_data = oauth_service.get_key_for_session(request.session_id)  # Need to implement this
    
    if not key_data or not key_data.encrypted_api_key:
        raise ValueError("OpenRouter not connected. Please connect in AI Settings.")
    
    # Decrypt and use the key
    decrypted_key = oauth_service.decrypt_api_key(key_data.encrypted_api_key)
    
    # Initialize OpenRouter client with decrypted key
    client = OpenRouterClient(api_key=decrypted_key)
    # ... rest of the code
```

**Option B: Use environment variable (Simple for testing)**

Set environment variable:
```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

The backend will fall back to this if no key is provided.

## 📝 Files to Modify

1. ✅ `frontend/src/services/chatService.js` - **CREATED**
2. ✅ `frontend/src/components/ChatInterface.vue` - **CREATED**
3. ❌ `frontend/src/components/ImageCard.vue` - **NEEDS UPDATE**
4. ❌ `frontend/src/App.vue` - **NEEDS UPDATE**
5. ❌ `backend/app/services/ai_chat_service.py` - **NEEDS UPDATE** (for Option A)

## 🎨 UI Features Implemented

- Clean, modern chat interface
- Message bubbles (blue for user, white for assistant)
- Typing indicator animation
- Operation tags showing what was applied
- Welcome message with example prompts
- Auto-scroll to latest message
- Error handling with red banners
- Connection status warning
- Mobile responsive design
- Smooth animations (fadeIn, slideUp, messageSlideIn)

## 🔧 Backend Integration Points

The chat service integrates with:
- `POST /api/v1/chat/send` - Send message and get AI response
- `GET /api/v1/chat/conversations/{id}` - Get conversation history
- `DELETE /api/v1/chat/conversations/{id}` - Delete conversation
- `GET /api/v1/chat/sessions/{id}/conversations` - List all conversations

## 📦 Available AI Operations

The AI can return these operations (backend processes them automatically):

- **brightness**: Adjust brightness (0.5-2.0)
- **contrast**: Adjust contrast (0.5-2.0)
- **saturation**: Adjust color saturation (0.0-2.0)
- **rotate**: Rotate image (-360 to 360 degrees)
- **crop**: Crop to specific region
- **resize**: Resize to specific dimensions
- **blur**: Apply blur effect (radius 1-10)
- **sharpen**: Sharpen image (factor 0.5-2.0)
- **sepia**: Apply sepia tone
- **grayscale**: Convert to grayscale

## 🚀 Next Steps After Implementation

1. Test various AI prompts
2. Test with different models (Gemini, Claude, GPT-4)
3. Add conversation history persistence
4. Add ability to view past conversations
5. Add ability to undo AI operations
6. Add image preview in chat (show before/after)
7. Add cost tracking display in chat
8. Add "Apply to all images" feature

## 🐛 Potential Issues to Watch For

1. **API Key**: Ensure OpenRouter is connected before opening chat
2. **Model Selection**: Verify a model is selected
3. **Session ID**: Must be properly passed to all components
4. **Image Refresh**: After operations, image should reload
5. **Scroll Position**: Chat should auto-scroll to bottom
6. **Loading State**: Prevent duplicate messages during loading
7. **Error Handling**: Show clear errors if API fails

## 📱 Mobile Considerations

- Chat modal takes 95% width on mobile
- Messages stack properly
- Input and button go full width on mobile
- Touch-friendly button sizes
- Proper keyboard handling

## 🎯 Success Criteria

- ✅ User can click chat button on image
- ✅ Chat modal opens with welcome message
- ✅ User can type and send messages
- ✅ AI responds with friendly text
- ✅ Operations are automatically applied to image
- ✅ Image refreshes to show changes
- ✅ Operation tags display in chat
- ✅ Error messages show if something fails
- ✅ Loading indicator shows while waiting
- ✅ Connection warning shows if not connected

## 🔐 Security Notes

- API keys stored encrypted in database
- Never exposed to frontend
- Session-based authentication
- Operations validated on backend
- File paths validated to prevent directory traversal

## 📚 Documentation

Add to user-facing docs:
- How to use AI chat
- Example prompts
- Supported operations
- Model recommendations
- Cost implications
- Limitations
