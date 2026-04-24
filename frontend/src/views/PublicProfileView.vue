<template>
  <div class="profile-page">
    <div v-if="loading" class="loading">Loading profile...</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else-if="profile" class="profile-container">

      <div class="avatar-section">
        <img :src="profile.avatar_url || defaultAvatar" class="avatar" alt="Avatar" />
      </div>

      <div class="profile-header">
        <h1>{{ profile.display_name || 'Player' }}</h1>
        <p class="member-since">Member since {{ memberSince }}</p>
      </div>

      <div class="profile-info">
        <p v-if="profile.bio" class="bio">{{ profile.bio }}</p>

        <div class="fields">
          <div v-if="profile.in_game_name" class="field-row">
            <span class="label">In-Game Name</span>
            <span>
              {{ profile.in_game_name }}
              <span v-if="profile.player_verified" class="badge verified">Verified</span>
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
        </div>

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

    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useProfile } from '@/composables/useProfile'

const route = useRoute()
const { profile, loading, error, fetchPublicProfile } = useProfile()

const defaultAvatar = computed(() => {
  const name = profile.value?.display_name || 'TE4'
  return `https://ui-avatars.com/api/?background=3BB143&color=fff&name=${encodeURIComponent(name)}`
})

const memberSince = computed(() => {
  if (!profile.value) return ''
  return new Date(profile.value.created_at).toLocaleDateString('en-GB', {
    year: 'numeric',
    month: 'long',
  })
})

onMounted(() => fetchPublicProfile(route.params.userId as string))
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
.stats-section {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--color-border);
}
.stats-section h2 {
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 12px;
  margin-bottom: 1rem;
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
</style>
