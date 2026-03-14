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
        this.sessionId = sessionOverride;

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

        await this.createSession(null, sessionOverride);
        return;
      }

      // Always call POST /sessions so the backend can resolve the canonical session.
      //
      // When an auth proxy (e.g. Authelia) is in use the backend reads the
      // Remote-User header and returns the existing session for that user,
      // making the session account-scoped.  Every browser used by the same
      // authenticated user will therefore share one session and see the same
      // images and mobile pairings.
      //
      // When there is no auth proxy the backend creates or returns the session
      // identified by the ID stored in localStorage, preserving the existing
      // single-user / anonymous behaviour.
      await this.createSession();
    },

    async createSession(userId = null, customSessionId = null) {
      this.isLoading = true;
      this.error = null;

      try {
        // Pass the locally-stored session ID as a hint so that in anonymous
        // (no-auth) mode the backend can return the same session the browser
        // was already using.  In authenticated mode the backend ignores this
        // hint and returns the canonical session for the logged-in user.
        const sessionOverride = import.meta.env.VITE_SESSION_OVERRIDE;
        const storedSessionId = (!sessionOverride || sessionOverride.trim() === '')
          ? localStorage.getItem('imagetools_session_id')
          : null;
        const hintId = customSessionId || storedSessionId || null;

        const session = await sessionService.createSession(userId, hintId);
        this.sessionId = session.id;
        this.sessionData = session;

        // Always persist the canonical session ID returned by the server.
        // In authenticated mode this overwrites any stale browser-local ID
        // with the account-scoped one so future loads skip the round-trip.
        if (!sessionOverride || sessionOverride.trim() === '') {
          localStorage.setItem('imagetools_session_id', session.id);
        }

        console.log('Session resolved:', this.sessionId);
      } catch (error) {
        this.error = error.message;
        console.error('Failed to resolve session:', error);
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
