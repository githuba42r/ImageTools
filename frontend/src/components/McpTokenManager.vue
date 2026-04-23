<template>
  <div class="mcp-token-manager">
    <div class="header">
      <h3>MCP Access Tokens</h3>
      <button @click="startCreate" :disabled="creating" class="btn btn-primary">
        + New Token
      </button>
    </div>

    <p class="help-text">
      Tokens let Claude Code (and other MCP clients) read your recent
      screenshots from ImageTools. Tokens are shown once at creation — copy
      immediately. Revoke any token you no longer need.
    </p>

    <!-- Create form -->
    <div v-if="creating" class="create-form">
      <input
        v-model="newLabel"
        type="text"
        placeholder="Label (e.g. laptop claude-code)"
        @keyup.enter="submitCreate"
        ref="labelInput"
      />
      <button @click="submitCreate" :disabled="!newLabel.trim()" class="btn btn-primary">
        Create
      </button>
      <button @click="creating = false" class="btn">Cancel</button>
    </div>

    <!-- Plaintext reveal (shown once) -->
    <div v-if="plaintextToken" class="plaintext-reveal">
      <p><strong>Copy this token now — it will not be shown again.</strong></p>
      <div class="token-row">
        <code>{{ plaintextToken }}</code>
        <button @click="copyToken" class="btn btn-sm">
          {{ copied ? 'Copied' : 'Copy' }}
        </button>
      </div>
      <button @click="plaintextToken = ''" class="btn btn-sm">Done</button>
    </div>

    <!-- Token list -->
    <table v-if="tokens.length" class="token-table">
      <thead>
        <tr>
          <th>Label</th>
          <th>Created</th>
          <th>Last used</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in tokens" :key="t.id">
          <td>{{ t.label }}</td>
          <td>{{ formatDate(t.created_at) }}</td>
          <td>{{ t.last_used_at ? formatDate(t.last_used_at) : '—' }}</td>
          <td>
            <button
              v-if="confirmingId !== t.id"
              @click="confirmingId = t.id"
              class="btn btn-sm btn-danger"
            >Revoke</button>
            <template v-else>
              <button @click="revoke(t.id)" class="btn btn-sm btn-danger">Confirm</button>
              <button @click="confirmingId = ''" class="btn btn-sm">Cancel</button>
            </template>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="!loading" class="empty">No tokens yet.</p>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue';
import { useUserStore } from '../stores/userStore';
import { storeToRefs } from 'pinia';
import { mcpTokenService } from '../services/api';

const userStore = useUserStore();
const { userId } = storeToRefs(userStore);

const tokens = ref([]);
const loading = ref(false);
const creating = ref(false);
const newLabel = ref('');
const plaintextToken = ref('');
const copied = ref(false);
const confirmingId = ref('');
const labelInput = ref(null);

const load = async () => {
  loading.value = true;
  try {
    tokens.value = await mcpTokenService.list(userId.value);
  } finally {
    loading.value = false;
  }
};

const startCreate = async () => {
  creating.value = true;
  newLabel.value = '';
  await nextTick();
  labelInput.value?.focus();
};

const submitCreate = async () => {
  if (!newLabel.value.trim()) return;
  const result = await mcpTokenService.create(userId.value, newLabel.value.trim());
  plaintextToken.value = result.token;
  creating.value = false;
  newLabel.value = '';
  copied.value = false;
  await load();
};

const copyToken = async () => {
  await navigator.clipboard.writeText(plaintextToken.value);
  copied.value = true;
};

const revoke = async (id) => {
  await mcpTokenService.revoke(userId.value, id);
  confirmingId.value = '';
  await load();
};

const formatDate = (iso) => new Date(iso).toLocaleString();

onMounted(load);
</script>

<style scoped>
.mcp-token-manager { padding: 1rem; }
.header { display: flex; justify-content: space-between; align-items: center; }
.help-text { color: #666; font-size: 0.9rem; margin: 0.5rem 0 1rem; }
.create-form { display: flex; gap: 0.5rem; margin: 1rem 0; }
.create-form input { flex: 1; padding: 0.4rem 0.6rem; }
.plaintext-reveal {
  background: #fffbea; border: 1px solid #e6c200; padding: 0.75rem;
  margin: 1rem 0; border-radius: 6px;
}
.token-row { display: flex; gap: 0.5rem; align-items: center; margin: 0.5rem 0; }
.token-row code {
  flex: 1; word-break: break-all; background: #fff; padding: 0.4rem;
  border: 1px solid #ddd; border-radius: 4px;
}
.token-table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
.token-table th, .token-table td {
  padding: 0.5rem; text-align: left; border-bottom: 1px solid #eee;
}
.btn {
  padding: 0.4rem 0.75rem; border: 1px solid #ccc; background: white;
  border-radius: 4px; cursor: pointer;
}
.btn-primary { background: #4CAF50; color: white; border-color: #4CAF50; }
.btn-danger { background: #d9534f; color: white; border-color: #d9534f; }
.btn-sm { padding: 0.25rem 0.5rem; font-size: 0.85rem; }
.empty { color: #999; font-style: italic; }
</style>
