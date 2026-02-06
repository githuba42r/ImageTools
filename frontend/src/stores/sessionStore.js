import { defineStore } from 'pinia';
import { sessionService } from '../services/api';

export const useSessionStore = defineStore('session', {
  state: () => ({
    sessionId: null,
    sessionData: null,
    isLoading: false,
    error: null,
  }),

  actions: {
    async initializeSession() {
      // Check localStorage for existing session
      const storedSessionId = localStorage.getItem('imagetools_session_id');

      if (storedSessionId) {
        // Validate stored session
        try {
          const validation = await sessionService.validateSession(storedSessionId);
          if (validation.valid) {
            this.sessionId = storedSessionId;
            this.sessionData = await sessionService.getSession(storedSessionId);
            console.log('Session restored:', this.sessionId);
            return;
          }
        } catch (error) {
          console.log('Stored session invalid, creating new session');
        }
      }

      // Create new session
      await this.createSession();
    },

    async createSession(userId = null) {
      this.isLoading = true;
      this.error = null;

      try {
        const session = await sessionService.createSession(userId);
        this.sessionId = session.id;
        this.sessionData = session;

        // Store in localStorage
        localStorage.setItem('imagetools_session_id', session.id);

        console.log('Session created:', this.sessionId);
      } catch (error) {
        this.error = error.message;
        console.error('Failed to create session:', error);
        throw error;
      } finally {
        this.isLoading = false;
      }
    },

    clearSession() {
      this.sessionId = null;
      this.sessionData = null;
      localStorage.removeItem('imagetools_session_id');
      console.log('Session cleared');
    },
  },
});
