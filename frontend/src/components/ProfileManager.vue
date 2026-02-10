<template>
  <div v-if="isOpen" class="modal-overlay" @click.self="closeModal">
    <div class="modal-content">
      <div class="modal-header">
        <h2>Manage Compression Profiles</h2>
        <button @click="closeModal" class="close-btn">×</button>
      </div>

      <div class="modal-body">
        <!-- Profile List -->
        <div class="profiles-section">
          <div class="section-header">
            <h3>Compression Profiles</h3>
            <button @click="showCreateForm" class="btn-primary">
              + New Profile
            </button>
          </div>

          <div v-if="profiles.length === 0" class="empty-state">
            <p>No profiles found. Please restart the backend to create system defaults.</p>
          </div>

          <div v-else class="profiles-list">
            <div
              v-for="profile in profiles"
              :key="profile.id"
              class="profile-item"
            >
              <div class="profile-info">
                <h4>
                  <span v-if="profile.system_default" class="profile-icon" title="System default profile">🔧</span>
                  <span v-else-if="profile.overrides_system_default" class="profile-icon" title="Custom profile (overrides system default)">🎨</span>
                  {{ profile.name }}
                </h4>
                <p class="profile-specs">
                  {{ profile.format }} • {{ profile.max_width }}×{{ profile.max_height }} •
                  Quality {{ profile.quality }} • ~{{ profile.target_size_kb }}KB
                </p>
              </div>

              <!-- Inline confirmation for delete/revert -->
              <div v-if="deletingProfileId === profile.id" class="inline-confirmation">
                <p class="confirmation-text">
                  {{ profile.overrides_system_default ? 'Revert to system default?' : 'Delete this profile?' }}
                </p>
                <div class="confirmation-actions">
                  <button @click="confirmDelete(profile)" class="btn-confirm" title="Confirm">
                    ✓
                  </button>
                  <button @click="cancelDelete" class="btn-cancel" title="Cancel">
                    ✕
                  </button>
                </div>
              </div>

              <!-- Normal action buttons -->
              <div v-else class="profile-actions">
                <button @click="editProfile(profile)" class="btn-edit" title="Edit">
                  ✏️
                </button>
                <button 
                  v-if="!profile.system_default"
                  @click="initiateDelete(profile)" 
                  class="btn-delete" 
                  :title="profile.overrides_system_default ? 'Revert to system default' : 'Delete'"
                >
                  {{ profile.overrides_system_default ? '↺' : '🗑️' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Create/Edit Form -->
        <div v-if="showForm" class="form-section">
          <h3>
            {{ editingProfile?.system_default ? 'Override System Profile' : editingProfile ? 'Edit Profile' : 'New Profile' }}
          </h3>
          <p v-if="editingProfile?.system_default" class="form-note">
            Saving will create your customized version of this profile with the same name, hiding the system default.
          </p>

          <form @submit.prevent="saveProfile">
            <div class="form-group">
              <label for="profile-name">Profile Name *</label>
              <input
                id="profile-name"
                v-model="formData.name"
                type="text"
                required
                placeholder="e.g., My Custom Profile"
                maxlength="100"
              />
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="max-width">Max Width (px) *</label>
                <input
                  id="max-width"
                  v-model.number="formData.max_width"
                  type="number"
                  required
                  min="100"
                  max="10000"
                />
              </div>

              <div class="form-group">
                <label for="max-height">Max Height (px) *</label>
                <input
                  id="max-height"
                  v-model.number="formData.max_height"
                  type="number"
                  required
                  min="100"
                  max="10000"
                />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="quality">Quality (1-100) *</label>
                <input
                  id="quality"
                  v-model.number="formData.quality"
                  type="number"
                  required
                  min="1"
                  max="100"
                />
              </div>

              <div class="form-group">
                <label for="target-size">Target Size (KB) *</label>
                <input
                  id="target-size"
                  v-model.number="formData.target_size_kb"
                  type="number"
                  required
                  min="10"
                  max="50000"
                />
              </div>
            </div>

            <div class="form-group">
              <label for="format">Output Format *</label>
              <select id="format" v-model="formData.format" required>
                <option value="JPEG">JPEG</option>
                <option value="PNG">PNG</option>
                <option value="WEBP">WEBP</option>
              </select>
            </div>

            <div class="form-group checkbox-group">
              <label>
                <input type="checkbox" v-model="formData.retain_aspect_ratio" />
                Retain image aspect ratio (recommended)
              </label>
            </div>

            <div class="form-actions">
              <button type="button" @click="cancelForm" class="btn-secondary">
                Cancel
              </button>
              <button type="submit" class="btn-primary" :disabled="saving">
                {{ saving ? 'Saving...' : 'Save Profile' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch } from 'vue'
import { profileService } from '../services/api'

export default {
  name: 'ProfileManager',
  props: {
    isOpen: {
      type: Boolean,
      required: true
    }
  },
  emits: ['close', 'updated'],
  setup(props, { emit }) {
    const profiles = ref([])
    const showForm = ref(false)
    const editingProfile = ref(null)
    const saving = ref(false)
    const deletingProfileId = ref(null)

    const formData = ref({
      name: '',
      max_width: 1920,
      max_height: 1920,
      quality: 85,
      target_size_kb: 500,
      format: 'JPEG',
      retain_aspect_ratio: true
    })

    const loadProfiles = async () => {
      try {
        const data = await profileService.getProfiles()
        profiles.value = data
      } catch (error) {
        console.error('Error loading profiles:', error)
        alert('Failed to load profiles. Please try again.')
      }
    }

    const showCreateForm = () => {
      editingProfile.value = null
      formData.value = {
        name: '',
        max_width: 1920,
        max_height: 1920,
        quality: 85,
        target_size_kb: 500,
        format: 'JPEG',
        retain_aspect_ratio: true
      }
      showForm.value = true
    }

    const copyProfile = (profile) => {
      editingProfile.value = null
      formData.value = {
        name: `${profile.name} (Copy)`,
        max_width: profile.max_width,
        max_height: profile.max_height,
        quality: profile.quality,
        target_size_kb: profile.target_size_kb,
        format: profile.format,
        retain_aspect_ratio: profile.retain_aspect_ratio
      }
      showForm.value = true
    }

    const editProfile = (profile) => {
      editingProfile.value = profile
      formData.value = {
        name: profile.name,
        max_width: profile.max_width,
        max_height: profile.max_height,
        quality: profile.quality,
        target_size_kb: profile.target_size_kb,
        format: profile.format,
        retain_aspect_ratio: profile.retain_aspect_ratio
      }
      showForm.value = true
    }

    const saveProfile = async () => {
      saving.value = true
      try {
        if (editingProfile.value) {
          await profileService.updateProfile(editingProfile.value.id, formData.value)
        } else {
          await profileService.createProfile(formData.value)
        }
        await loadProfiles()
        showForm.value = false
        emit('updated')
      } catch (error) {
        console.error('Error saving profile:', error)
        alert('Failed to save profile. Please try again.')
      } finally {
        saving.value = false
      }
    }

    const initiateDelete = (profile) => {
      deletingProfileId.value = profile.id
    }

    const cancelDelete = () => {
      deletingProfileId.value = null
    }

    const confirmDelete = async (profile) => {
      try {
        await profileService.deleteProfile(profile.id)
        await loadProfiles()
        deletingProfileId.value = null
        emit('updated')
      } catch (error) {
        console.error('Error deleting profile:', error)
        alert('Failed to delete profile. Please try again.')
      }
    }

    const resetProfile = async (profile) => {
      // TODO: Implement reset functionality
      // This would delete any user override and revert to system default
      alert('Reset functionality coming soon!')
    }

    const cancelForm = () => {
      showForm.value = false
      editingProfile.value = null
    }

    const closeModal = () => {
      if (showForm.value) {
        if (confirm('You have unsaved changes. Are you sure you want to close?')) {
          showForm.value = false
          editingProfile.value = null
          emit('close')
        }
      } else {
        emit('close')
      }
    }

    // Load profiles when modal opens
    watch(() => props.isOpen, (newValue) => {
      if (newValue) {
        loadProfiles()
      }
    }, { immediate: true })

    return {
      profiles,
      showForm,
      editingProfile,
      formData,
      saving,
      deletingProfileId,
      showCreateForm,
      copyProfile,
      editProfile,
      saveProfile,
      initiateDelete,
      cancelDelete,
      confirmDelete,
      resetProfile,
      cancelForm,
      closeModal
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}

.close-btn {
  background: none;
  border: none;
  font-size: 32px;
  line-height: 1;
  color: #9ca3af;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
}

.close-btn:hover {
  color: #4b5563;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.profiles-section {
  margin-bottom: 32px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #6b7280;
}

.profiles-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.profile-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  transition: border-color 0.2s;
}

.profile-item:hover {
  border-color: #d1d5db;
}

.profile-icon {
  font-size: 16px;
  margin-right: 6px;
}

.profile-info {
  flex: 1;
}

.profile-info h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 8px;
}

.profile-specs {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
}

.profile-actions {
  display: flex;
  gap: 8px;
}

.inline-confirmation {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #fef3c7;
  border-radius: 6px;
  border: 1px solid #fbbf24;
}

.confirmation-text {
  margin: 0;
  font-size: 13px;
  font-weight: 500;
  color: #92400e;
  white-space: nowrap;
}

.confirmation-actions {
  display: flex;
  gap: 6px;
}

.btn-confirm,
.btn-cancel {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
  line-height: 1;
}

.btn-confirm {
  color: #059669;
}

.btn-confirm:hover {
  background: #d1fae5;
}

.btn-cancel {
  color: #dc2626;
}

.btn-cancel:hover {
  background: #fee2e2;
}

.btn-edit,
.btn-delete {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.btn-edit:hover {
  background: #f3f4f6;
}

.btn-delete:hover {
  background: #fee2e2;
}

.form-section {
  border-top: 1px solid #e5e7eb;
  padding-top: 24px;
}

.form-section h3 {
  margin: 0 0 20px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.form-note {
  margin: -10px 0 20px 0;
  padding: 12px;
  background: #fef3c7;
  border-left: 3px solid #f59e0b;
  border-radius: 4px;
  font-size: 13px;
  color: #92400e;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-weight: 400;
}

.checkbox-group input[type="checkbox"] {
  width: auto;
  cursor: pointer;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
}

.btn-primary,
.btn-secondary {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

@media (max-width: 640px) {
  .modal-content {
    max-width: 100%;
    max-height: 100vh;
    border-radius: 0;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .profile-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .profile-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
