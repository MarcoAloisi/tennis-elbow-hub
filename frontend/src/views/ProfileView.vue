<template>
  <div class="profile-page">
    <div v-if="loading" class="loading">Loading profile...</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else-if="profile" class="profile-container">

      <!-- Avatar -->
      <div class="avatar-section">
        <img :src="profile.avatar_url || defaultAvatar" class="avatar" alt="Avatar" />
        <div v-if="editMode" class="avatar-upload">
          <label class="upload-label">
            Change Avatar
            <input type="file" accept="image/jpeg,image/png,image/webp" @change="handleAvatarChange" hidden />
          </label>
          <p class="hint">Max 2MB · JPEG, PNG, WebP</p>
        </div>
      </div>

      <!-- Header -->
      <div class="profile-header">
        <h1>{{ profile.display_name || 'No name set' }}</h1>
        <p class="member-since">Member since {{ memberSince }}</p>
        <button class="edit-btn" @click="toggleEdit">
          {{ editMode ? 'Cancel' : 'Edit Profile' }}
        </button>
      </div>

      <!-- View mode -->
      <div v-if="!editMode" class="profile-info">
        <p v-if="profile.bio" class="bio">{{ profile.bio }}</p>

        <div class="fields">
          <div v-if="profile.in_game_name" class="field-row">
            <span class="label">In-Game Name</span>
            <span>
              {{ profile.in_game_name }}
              <span v-if="profile.player_verified" class="badge verified">Verified</span>
              <span v-else-if="profile.player_name" class="badge pending">Pending Approval</span>
            </span>
          </div>
          <div v-if="profile.tours?.length" class="field-row">
            <span class="label">Tours</span>
            <span>{{ profile.tours.map(t => t.toUpperCase()).join(', ') }}</span>
          </div>
          <div v-if="profile.favorite_tennis_player" class="field-row">
            <span class="label">Favourite Player</span>
            <span>{{ profile.favorite_tennis_player }}</span>
          </div>
          <div v-if="profile.favorite_tournament" class="field-row">
            <span class="label">Favourite Tournament</span>
            <span>{{ profile.favorite_tournament }}</span>
          </div>
          <div v-if="profile.birthday" class="field-row">
            <span class="label">Birthday</span>
            <span>{{ profile.birthday }}</span>
          </div>
        </div>

        <!-- Player stats -->
        <div v-if="profile.player_verified && profile.player_stats" class="stats-section">
          <h2>Player Stats</h2>
          <div class="stats-grid">
            <div class="stat">
              <span class="stat-val">{{ profile.player_stats.total_matches }}</span>
              <span class="stat-label">Matches</span>
            </div>
            <div class="stat">
              <span class="stat-val">{{ profile.player_stats.wins }}</span>
              <span class="stat-label">Wins</span>
            </div>
            <div class="stat">
              <span class="stat-val">{{ profile.player_stats.losses }}</span>
              <span class="stat-label">Losses</span>
            </div>
            <div class="stat">
              <span class="stat-val">{{ profile.player_stats.latest_elo ?? '—' }}</span>
              <span class="stat-label">ELO</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Edit mode -->
      <form v-else class="edit-form" @submit.prevent="saveProfile">
        <div class="field">
          <label>Display Name</label>
          <input v-model="form.display_name" type="text" />
        </div>
        <div class="field">
          <label>Bio</label>
          <textarea v-model="form.bio" rows="3" placeholder="Tell the community about yourself..."></textarea>
        </div>
        <div class="field">
          <label>Birthday</label>
          <input v-model="form.birthday" type="date" />
        </div>
        <div class="field">
          <label>Tours</label>
          <div class="checkbox-group">
            <label class="checkbox">
              <input type="checkbox" value="xkt" v-model="form.tours" /> XKT
            </label>
            <label class="checkbox">
              <input type="checkbox" value="wtsl" v-model="form.tours" /> WTSL
            </label>
          </div>
        </div>
        <div class="field">
          <label>In-Game Name</label>
          <input v-model="form.in_game_name" type="text" placeholder="Your in-game display name" />
        </div>
        <div class="field">
          <label>Link to Player Record</label>
          <select v-model="form.player_name">
            <option value="">— not linked —</option>
            <option v-for="p in players" :key="p" :value="p">{{ p }}</option>
          </select>
          <p class="hint">Select your player record from the database. Requires admin approval to show stats.</p>
        </div>
        <div class="field">
          <label>Favourite Tennis Player</label>
          <input v-model="form.favorite_tennis_player" type="text" />
        </div>
        <div class="field">
          <label>Favourite Tournament</label>
          <input v-model="form.favorite_tournament" type="text" />
        </div>

        <p v-if="saveError" class="error-msg">{{ saveError }}</p>
        <button type="submit" :disabled="saving">{{ saving ? 'Saving...' : 'Save Changes' }}</button>
      </form>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useProfile } from '@/composables/useProfile'

const { profile, loading, error, fetchMyProfile, updateProfile, uploadAvatar, fetchPlayers } = useProfile()

const editMode = ref(false)
const saving = ref(false)
const saveError = ref<string | null>(null)
const players = ref<string[]>([])

const defaultAvatar = computed(() => {
  const name = profile.value?.display_name || 'TE4'
  return `https://ui-avatars.com/api/?background=3BB143&color=fff&name=${encodeURIComponent(name)}`
})

const form = ref({
  display_name: '',
  bio: '',
  birthday: '',
  tours: [] as string[],
  in_game_name: '',
  player_name: '',
  favorite_tennis_player: '',
  favorite_tournament: '',
})

const memberSince = computed(() => {
  if (!profile.value) return ''
  return new Date(profile.value.created_at).toLocaleDateString('en-GB', {
    year: 'numeric',
    month: 'long',
  })
})

function toggleEdit() {
  if (!editMode.value && profile.value) {
    form.value = {
      display_name: profile.value.display_name || '',
      bio: profile.value.bio || '',
      birthday: profile.value.birthday || '',
      tours: profile.value.tours ? [...profile.value.tours] : [],
      in_game_name: profile.value.in_game_name || '',
      player_name: profile.value.player_name || '',
      favorite_tennis_player: profile.value.favorite_tennis_player || '',
      favorite_tournament: profile.value.favorite_tournament || '',
    }
  }
  editMode.value = !editMode.value
}

async function saveProfile() {
  saving.value = true
  saveError.value = null
  try {
    await updateProfile({
      ...form.value,
      birthday: form.value.birthday || null,
      player_name: form.value.player_name || null,
    })
    editMode.value = false
  } catch (e: any) {
    saveError.value = e.message || 'Failed to save'
  } finally {
    saving.value = false
  }
}

async function handleAvatarChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  await uploadAvatar(file)
}

onMounted(async () => {
  await fetchMyProfile()
  players.value = await fetchPlayers()
})
</script>

<style scoped>
.profile-page {
  max-width: 700px;
  margin: 2rem auto;
  padding: 0 1rem;
}
.loading {
  text-align: center;
  padding: 4rem;
  color: var(--color-text-secondary);
}
.error-msg {
  color: var(--color-error);
  text-align: center;
  padding: 2rem;
}
.avatar-section {
  text-align: center;
  margin-bottom: 1.5rem;
}
.avatar {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid var(--color-brand-primary);
}
.avatar-upload {
  margin-top: 12px;
}
.upload-label {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 6px;
  border: 1px solid var(--color-brand-primary);
  color: var(--color-brand-primary);
  cursor: pointer;
  font-size: 14px;
}
.profile-header {
  text-align: center;
  margin-bottom: 2rem;
}
.profile-header h1 {
  font-size: 1.8rem;
  margin-bottom: 4px;
}
.member-since {
  color: var(--color-text-secondary);
  font-size: 14px;
  margin-bottom: 12px;
}
.edit-btn {
  padding: 8px 20px;
  border-radius: 6px;
  border: 1px solid var(--color-brand-primary);
  background: transparent;
  color: var(--color-brand-primary);
  cursor: pointer;
  font-size: 14px;
}
.bio {
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin-bottom: 1.5rem;
}
.fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 2rem;
}
.field-row {
  display: flex;
  gap: 12px;
  align-items: baseline;
}
.label {
  font-weight: 600;
  min-width: 170px;
  color: var(--color-text-secondary);
  font-size: 14px;
}
.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 99px;
  margin-left: 8px;
  font-weight: 600;
}
.badge.verified {
  background: var(--color-success);
  color: #000;
}
.badge.pending {
  background: var(--color-warning, #F59E0B);
  color: #000;
}
.stats-section {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--color-border);
}
.stats-section h2 {
  font-size: 1.1rem;
  margin-bottom: 1rem;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 12px;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.stat {
  background: var(--color-bg-secondary);
  border-radius: 8px;
  padding: 1rem;
  text-align: center;
  border: 1px solid var(--color-border);
}
.stat-val {
  display: block;
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--color-brand-primary);
}
.stat-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}
.edit-form .field {
  margin-bottom: 1.2rem;
}
.edit-form label {
  display: block;
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
  font-weight: 500;
}
.edit-form input,
.edit-form textarea,
.edit-form select {
  width: 100%;
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
  font-size: 14px;
  box-sizing: border-box;
}
.checkbox-group {
  display: flex;
  gap: 20px;
}
.checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 14px;
}
.hint {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 4px;
}
button[type="submit"] {
  padding: 12px 32px;
  border-radius: 6px;
  background: var(--color-brand-primary);
  color: var(--color-text-inverse);
  border: none;
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
}
button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
