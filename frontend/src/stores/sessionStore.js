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
      // Check for session override from environment (for testing multi-user sessions)
      const sessionOverride = import.meta.env.VITE_SESSION_OVERRIDE;
      
      if (sessionOverride && sessionOverride.trim() !== '') {
        console.log('Using session override:', sessionOverride);
        // Use override value as session ID
        this.sessionId = sessionOverride;
        
        // Try to validate and get session data
        try {
          const validation = await sessionService.validateSession(sessionOverride);
          if (validation.valid) {
            this.sessionData = await sessionService.getSession(sessionOverride);
            console.log('Session override validated:', this.sessionId);
            return;
          }
        } catch (error) {
          console.log('Session override not found, creating new session with ID:', sessionOverride);
        }
        
        // Create session with override ID
        await this.createSession(null, sessionOverride);
        return;
      }
      
      // Normal flow: Check localStorage for existing session
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

    async createSession(userId = null, customSessionId = null) {
      this.isLoading = true;
      this.error = null;

      try {
        const session = await sessionService.createSession(userId, customSessionId);
        this.sessionId = session.id;
        this.sessionData = session;

        // Store in localStorage only if not using override
        const sessionOverride = import.meta.env.VITE_SESSION_OVERRIDE;
        if (!sessionOverride || sessionOverride.trim() === '') {
          localStorage.setItem('imagetools_session_id', session.id);
        }

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
