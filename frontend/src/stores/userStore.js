import { defineStore } from 'pinia';
import { userService } from '../services/api';

export const useUserStore = defineStore('user', {
  state: () => ({
    userId: null,
    userData: null,
    isLoading: false,
    error: null,
  }),

  actions: {
    async initializeUser() {
      // Check for user override from environment (for testing multi-user scenarios)
      const userOverride = import.meta.env.VITE_USER_OVERRIDE;

      if (userOverride && userOverride.trim() !== '') {
        console.log('Using user override:', userOverride);
        this.userId = userOverride;

        try {
          const validation = await userService.validateUser(userOverride);
          if (validation.valid) {
            this.userData = await userService.getUser(userOverride);
            console.log('User override validated:', this.userId);
            return;
          }
        } catch (error) {
          console.log('User override not found, creating new user with ID:', userOverride);
        }

        await this.getOrCreateUser(userOverride);
        return;
      }

      // Always call POST /users so the backend can resolve the canonical user.
      //
      // When an auth proxy (e.g. Authelia) is in use the backend reads the
      // Remote-User header and returns the existing user for that username,
      // making the user account-scoped.  Every browser used by the same
      // authenticated user will therefore share one user record and see the same
      // images and mobile pairings.
      //
      // When there is no auth proxy the backend creates or returns the user
      // identified by the ID stored in localStorage, preserving the existing
      // single-user / anonymous behaviour.
      await this.getOrCreateUser();
    },

    async getOrCreateUser(hintId = null) {
      this.isLoading = true;
      this.error = null;

      try {
        // Pass the locally-stored user ID as a hint so that in anonymous
        // (no-auth) mode the backend can return the same user the browser
        // was already using.  In authenticated mode the backend ignores this
        // hint and returns the canonical user for the logged-in account.
        const userOverride = import.meta.env.VITE_USER_OVERRIDE;
        const storedUserId = (!userOverride || userOverride.trim() === '')
          ? localStorage.getItem('imagetools_user_id')
          : null;
        const resolvedHintId = hintId || storedUserId || null;

        const user = await userService.getOrCreateUser(resolvedHintId);
        this.userId = user.id;
        this.userData = user;

        // Always persist the canonical user ID returned by the server.
        // In authenticated mode this overwrites any stale browser-local ID
        // with the account-scoped one so future loads skip the round-trip.
        if (!userOverride || userOverride.trim() === '') {
          localStorage.setItem('imagetools_user_id', user.id);
        }

        console.log('User resolved:', this.userId);
      } catch (error) {
        this.error = error.message;
        console.error('Failed to resolve user:', error);
        throw error;
      } finally {
        this.isLoading = false;
      }
    },

    clearUser() {
      this.userId = null;
      this.userData = null;
      localStorage.removeItem('imagetools_user_id');
      console.log('User cleared');
    },
  },
});
