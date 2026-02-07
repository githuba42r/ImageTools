/**
 * AI Chat Service
 * 
 * Handles AI chat API communication for image manipulation
 */

class ChatService {
  constructor() {
    // Use relative URL - Vite proxy handles dev, production serves from same origin
    this.baseURL = '/api/v1/chat';
    this.sessionId = null;
  }

  /**
   * Set the session ID for API requests
   * @param {string} sessionId - Current session ID
   */
  setSessionId(sessionId) {
    this.sessionId = sessionId;
  }

  /**
   * Get headers with session ID
   * @returns {Object} Headers object
   */
  _getHeaders() {
    const headers = {
      'Content-Type': 'application/json',
    };
    
    if (this.sessionId) {
      headers['X-Session-ID'] = this.sessionId;
    }
    
    return headers;
  }

  /**
   * Send a message in a conversation
   * @param {Object} params - Message parameters
   * @param {string} params.message - User message
   * @param {string} params.imageId - Image ID
   * @param {string} params.conversationId - Optional conversation ID
   * @param {string} params.model - Optional model ID
   * @returns {Promise<Object>} Chat response with AI reply and operations
   */
  async sendMessage({ message, imageId, conversationId, model }) {
    if (!this.sessionId) {
      throw new Error('Session ID not set. Please initialize chat service first.');
    }
    
    const response = await fetch(`${this.baseURL}/send`, {
      method: 'POST',
      headers: this._getHeaders(),
      body: JSON.stringify({
        session_id: this.sessionId,
        message,
        image_id: imageId,
        conversation_id: conversationId,
        model: model || undefined
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to send message');
    }

    return response.json();
  }

  /**
   * Get a conversation with all messages
   * @param {string} conversationId - Conversation ID
   * @returns {Promise<Object>} Conversation with messages
   */
  async getConversation(conversationId) {
    const response = await fetch(`${this.baseURL}/conversations/${conversationId}`, {
      method: 'GET',
      headers: this._getHeaders()
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get conversation');
    }

    return response.json();
  }

  /**
   * Get all conversations for the current session
   * @param {string} sessionId - Session ID
   * @returns {Promise<Array>} List of conversations
   */
  async getSessionConversations(sessionId) {
    const response = await fetch(`${this.baseURL}/sessions/${sessionId}/conversations`, {
      method: 'GET',
      headers: this._getHeaders()
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get conversations');
    }

    return response.json();
  }

  /**
   * Delete a conversation
   * @param {string} conversationId - Conversation ID
   * @returns {Promise<Object>} Success response
   */
  async deleteConversation(conversationId) {
    const response = await fetch(`${this.baseURL}/conversations/${conversationId}`, {
      method: 'DELETE',
      headers: this._getHeaders()
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete conversation');
    }

    return response.json();
  }
}

// Export singleton instance
export const chatService = new ChatService();
