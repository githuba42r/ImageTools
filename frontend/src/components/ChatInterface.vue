<template>
  <div class="chat-modal-overlay" @click="handleCloseClick">
    <div class="chat-modal" @click.stop>
      <button class="modal-close-btn" @click="$emit('close')">✕</button>
      
      <div class="chat-header">
        <div class="header-info">
          <h2>🤖 AI Chat</h2>
          <p class="image-name">{{ image.original_filename }}</p>
        </div>
      </div>
      
      <div class="chat-messages" ref="messagesContainer">
        <div v-if="messages.length === 0" class="welcome-message">
          <span class="welcome-icon">💬</span>
          <h3>AI Image Manipulation</h3>
          <p>Ask me to modify your image! For example:</p>
          <ul>
            <li>"Make it brighter"</li>
            <li>"Add more contrast and saturation"</li>
            <li>"Rotate it 90 degrees"</li>
            <li>"Make it grayscale"</li>
          </ul>
        </div>
        
        <div 
          v-for="(message, index) in messages" 
          :key="index"
          class="message"
          :class="{ 'user-message': message.role === 'user', 'assistant-message': message.role === 'assistant' }"
        >
          <div class="message-icon">
            {{ message.role === 'user' ? '👤' : '🤖' }}
          </div>
          <div class="message-content">
            <div class="message-text">{{ message.content }}</div>
            <div v-if="message.operations && message.operations.length > 0" class="operations-info">
              <span class="operations-label">Applied operations:</span>
              <span 
                v-for="(op, idx) in message.operations" 
                :key="idx"
                class="operation-tag"
              >
                {{ op.type }}
              </span>
            </div>
            <div v-if="message.timestamp" class="message-time">
              {{ formatTime(message.timestamp) }}
            </div>
          </div>
        </div>
        
        <div v-if="isLoading" class="message assistant-message loading">
          <div class="message-icon">🤖</div>
          <div class="message-content">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="chat-input-container">
        <div v-if="error" class="error-message">
          {{ error }}
        </div>
        <form @submit.prevent="sendMessage" class="chat-input-form">
          <input 
            v-model="inputMessage"
            type="text"
            placeholder="Ask AI to modify the image..."
            class="chat-input"
            :disabled="isLoading || !isConnected"
            ref="messageInput"
          />
          <button 
            type="submit"
            class="send-button"
            :disabled="!inputMessage.trim() || isLoading || !isConnected"
          >
            <span v-if="!isLoading">Send</span>
            <span v-else>...</span>
          </button>
        </form>
        <div v-if="!isConnected" class="connection-warning">
          <span>⚠️</span>
          <span>Connect to OpenRouter and select a model in AI Settings to use chat</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue';
import { chatService } from '../services/chatService';

const props = defineProps({
  image: {
    type: Object,
    required: true
  },
  sessionId: {
    type: String,
    required: true
  },
  selectedModel: {
    type: String,
    default: null
  },
  isConnected: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['close', 'operationsApplied']);

const messages = ref([]);
const inputMessage = ref('');
const isLoading = ref(false);
const error = ref(null);
const conversationId = ref(null);
const messagesContainer = ref(null);
const messageInput = ref(null);

onMounted(() => {
  // Set session ID for chat service
  chatService.setSessionId(props.sessionId);
  
  // Focus input
  if (messageInput.value) {
    messageInput.value.focus();
  }
});

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value || !props.isConnected) {
    return;
  }
  
  const userMessage = inputMessage.value.trim();
  error.value = null;
  
  // Add user message to UI
  messages.value.push({
    role: 'user',
    content: userMessage,
    timestamp: new Date()
  });
  
  inputMessage.value = '';
  isLoading.value = true;
  
  // Scroll to bottom
  await nextTick();
  scrollToBottom();
  
  try {
    const response = await chatService.sendMessage({
      message: userMessage,
      imageId: props.image.id,
      conversationId: conversationId.value,
      model: props.selectedModel
    });
    
    // Store conversation ID for future messages
    if (!conversationId.value) {
      conversationId.value = response.conversation_id;
    }
    
    // Add assistant response to UI
    messages.value.push({
      role: 'assistant',
      content: response.reply,
      operations: response.operations || [],
      timestamp: new Date()
    });
    
    // Emit event if operations were applied
    if (response.operations && response.operations.length > 0) {
      emit('operationsApplied', response.operations);
    }
    
    // Scroll to bottom
    await nextTick();
    scrollToBottom();
    
  } catch (err) {
    console.error('Chat error:', err);
    error.value = err.message || 'Failed to send message';
    
    // Remove the user message if sending failed
    messages.value.pop();
    inputMessage.value = userMessage; // Restore the message
  } finally {
    isLoading.value = false;
  }
};

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

const formatTime = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit' 
  });
};

const handleCloseClick = (event) => {
  if (event.target.classList.contains('chat-modal-overlay')) {
    emit('close');
  }
};

// Watch for new messages and scroll
watch(messages, async () => {
  await nextTick();
  scrollToBottom();
}, { deep: true });
</script>

<style scoped>
.chat-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.chat-modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 700px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease;
  position: relative;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-close-btn {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: none;
  border: none;
  font-size: 2rem;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s ease;
  z-index: 10;
  line-height: 1;
}

.modal-close-btn:hover {
  color: #333;
}

.chat-header {
  padding: 1.5rem 1.5rem 1rem 1.5rem;
  border-bottom: 1px solid #e0e0e0;
  background: linear-gradient(to bottom, #f8f9fa 0%, #ffffff 100%);
  border-radius: 12px 12px 0 0;
}

.header-info h2 {
  margin: 0 0 0.25rem 0;
  font-size: 1.5rem;
  color: #333;
}

.image-name {
  margin: 0;
  font-size: 0.85rem;
  color: #666;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background-color: #f8f9fa;
}

.welcome-message {
  text-align: center;
  padding: 2rem 1rem;
  color: #666;
}

.welcome-icon {
  font-size: 3rem;
  display: block;
  margin-bottom: 1rem;
}

.welcome-message h3 {
  margin: 0 0 0.5rem 0;
  color: #333;
  font-size: 1.25rem;
}

.welcome-message p {
  margin: 0 0 1rem 0;
  color: #666;
}

.welcome-message ul {
  text-align: left;
  display: inline-block;
  margin: 0;
  padding-left: 1.5rem;
}

.welcome-message li {
  margin: 0.5rem 0;
  color: #555;
  font-style: italic;
}

.message {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  animation: messageSlideIn 0.3s ease;
}

@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-icon {
  font-size: 1.75rem;
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background-color: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.message-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.message-text {
  background-color: white;
  padding: 0.875rem 1rem;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  line-height: 1.5;
  color: #333;
  word-wrap: break-word;
}

.user-message .message-text {
  background-color: #2196F3;
  color: white;
}

.assistant-message .message-text {
  background-color: white;
}

.operations-info {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  padding: 0.5rem 0;
}

.operations-label {
  font-size: 0.8rem;
  color: #666;
  font-weight: 600;
}

.operation-tag {
  padding: 0.25rem 0.75rem;
  background-color: #e3f2fd;
  color: #1976D2;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: capitalize;
}

.message-time {
  font-size: 0.75rem;
  color: #999;
  text-align: right;
}

.typing-indicator {
  display: flex;
  gap: 0.35rem;
  padding: 1rem;
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  width: fit-content;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background-color: #999;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-10px);
  }
}

.chat-input-container {
  padding: 1rem 1.5rem;
  border-top: 1px solid #e0e0e0;
  background-color: white;
  border-radius: 0 0 12px 12px;
}

.error-message {
  background-color: #ffebee;
  color: #c62828;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
}

.chat-input-form {
  display: flex;
  gap: 0.75rem;
}

.chat-input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.2s ease;
}

.chat-input:focus {
  outline: none;
  border-color: #2196F3;
}

.chat-input:disabled {
  background-color: #f5f5f5;
  cursor: not-allowed;
}

.send-button {
  padding: 0.75rem 1.5rem;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 80px;
}

.send-button:hover:not(:disabled) {
  background-color: #1976D2;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(33, 150, 243, 0.3);
}

.send-button:disabled {
  background-color: #e0e0e0;
  color: #999;
  cursor: not-allowed;
  transform: none;
}

.connection-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.75rem;
  padding: 0.75rem;
  background-color: #fff3cd;
  color: #856404;
  border-radius: 6px;
  font-size: 0.85rem;
}

@media (max-width: 768px) {
  .chat-modal {
    width: 95%;
    max-height: 90vh;
  }
  
  .chat-messages {
    padding: 1rem;
  }
  
  .message-icon {
    width: 32px;
    height: 32px;
    font-size: 1.5rem;
  }
  
  .chat-input-form {
    flex-direction: column;
  }
  
  .send-button {
    width: 100%;
  }
}
</style>
