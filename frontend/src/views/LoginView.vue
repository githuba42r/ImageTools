<template>
  <div class="login-screen">
    <div class="login-card">
      <h1>ImageTools</h1>
      <p>Sign in with your vinCreative account to access your images.</p>
      <div v-if="errorMessage" class="login-error" role="alert">
        {{ errorMessage }}
      </div>
      <button class="login-button" @click="signIn">Sign in</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const errorMessage = computed(() => {
  const params = new URLSearchParams(window.location.search)
  const err = params.get('login_error')
  if (!err) return null
  // Friendly messages for known cases; otherwise show raw
  switch (true) {
    case err.startsWith('token_invalid'): return 'Sign-in failed: the identity token was rejected.'
    case err === 'state_mismatch':        return 'Sign-in expired or was tampered with. Please try again.'
    case err === 'idp_unreachable':       return 'The identity provider is currently unreachable. Please try again shortly.'
    case err === 'access_denied':         return 'Access was denied at the identity provider.'
    default:                              return `Sign-in error: ${decodeURIComponent(err)}`
  }
})

function signIn() {
  const ret = encodeURIComponent(window.location.pathname + window.location.search)
  window.location.href = `/api/v1/oauth2/connect?return=${ret}`
}
</script>

<style scoped>
.login-screen {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1a1a1a;
  color: #eee;
}
.login-card {
  background: #2a2a2a;
  padding: 2rem 3rem;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  max-width: 380px;
  text-align: center;
}
.login-card h1 { margin: 0 0 0.5rem; }
.login-card p  { margin: 0 0 1.5rem; opacity: 0.75; }
.login-button {
  padding: 0.75rem 1.5rem;
  background: #4a9eff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
}
.login-button:hover { background: #3a8eef; }
.login-error {
  background: #4a1a1a;
  color: #f88;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}
</style>
