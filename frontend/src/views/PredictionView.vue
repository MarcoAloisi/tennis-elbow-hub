<!-- frontend/src/views/PredictionView.vue -->
<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { usePredictionsStore, type PickData, type DrawMatch } from '@/stores/predictions'
import { useAuthStore } from '@/stores/auth'
import BracketEditor from '@/components/predictions/BracketEditor.vue'
import PredictionLeaderboard from '@/components/predictions/PredictionLeaderboard.vue'
import AllPredictions from '@/components/predictions/AllPredictions.vue'
import AdminPanel from '@/components/predictions/AdminPanel.vue'
import ScoringLegend from '@/components/predictions/ScoringLegend.vue'

const store = usePredictionsStore()
const authStore = useAuthStore()

const activeTab = ref<'prediction' | 'draw' | 'leaderboard' | 'all'>('prediction')
const nicknameInput = ref(store.myNickname)
const submitError = ref<string | null>(null)
const submitSuccess = ref(false)

const tournament = computed(() => {
    // Active = first open or closed tournament; else null
    return store.tournaments.find(t => t.status !== 'finished') ?? null
})

const isOpen = computed(() => tournament.value?.status === 'open')
const isPredictionsClosed = computed(() => (tournament.value?.status ?? '') !== 'open')
const deadlinePassed = computed(() => {
    if (!tournament.value) return false
    return new Date() > new Date(tournament.value.predictions_close_at)
})
const alreadySubmitted = computed(() =>
    tournament.value ? store.hasSubmitted(tournament.value.id) : false
)
const canSubmit = computed(() =>
    isOpen.value && !deadlinePassed.value && !alreadySubmitted.value
)

const pastTournaments = computed(() =>
    store.tournaments.filter(t => t.status === 'finished')
)

onMounted(async () => {
    await store.fetchTournaments()
    if (tournament.value) {
        await Promise.all([
            store.fetchTournament(tournament.value.slug),
            store.fetchEntries(tournament.value.id),
        ])
    }
})

watch(() => tournament.value?.id, async (id) => {
    if (id) {
        await Promise.all([
            store.fetchTournament(tournament.value!.slug),
            store.fetchEntries(id),
        ])
    }
})

async function handleSubmit() {
    submitError.value = null
    const nick = nicknameInput.value.trim()
    if (!nick) { submitError.value = 'Please enter a nickname'; return }
    if (!tournament.value) return
    try {
        await store.submitPrediction(tournament.value.id, nick)
        submitSuccess.value = true
    } catch (err: any) {
        submitError.value = err.message
    }
}

function handlePick(matchId: string, patch: Partial<PickData>) {
    store.setPick(matchId, patch)
}

// Readonly "actual draw" picks: map every played match to {winner: actualWinner}
// so BracketEditor highlights winners exactly like the scraper recorded.
const actualPicks = computed<Record<string, PickData>>(() => {
    const out: Record<string, PickData> = {}
    const matches = store.activeTournament?.draw_data?.matches ?? []
    for (const m of matches as DrawMatch[]) {
        if (m.winner) out[m.id] = { winner: m.winner }
    }
    return out
})

const hasQualifyingMatches = computed(() =>
    (store.activeTournament?.draw_data?.matches ?? []).some(m => m.section === 'qualifying')
)

async function onAdminRefresh() {
    await store.fetchTournaments()
    if (tournament.value) {
        await Promise.all([
            store.fetchTournament(tournament.value.slug),
            store.fetchEntries(tournament.value.id),
        ])
    } else {
        store.activeTournament = null
        store.entries = []
    }
}

function formatDeadline(dt: string) {
    return new Date(dt).toLocaleString(undefined, {
        dateStyle: 'medium', timeStyle: 'short'
    })
}
</script>

<template>
    <div class="prediction-view">
        <div class="page-header">
            <h1>Tournament Predictions</h1>
            <p class="intro">Pick winners, predict how many sets each match goes (or a retirement), and earn points. Top 3 go on the podium.</p>
        </div>

        <!-- Admin panel -->
        <AdminPanel
            v-if="authStore.isAdmin"
            :tournament="store.activeTournament"
            @refresh="onAdminRefresh"
        />

        <!-- Active tournament -->
        <div v-if="store.activeTournament" class="tournament-section">
            <!-- Banner -->
            <div class="tournament-banner">
                <div>
                    <div class="trn-name">{{ store.activeTournament.name }}</div>
                    <div class="trn-meta">
                        {{ store.activeTournament.draw_data?.surface }} ·
                        {{ store.activeTournament.draw_data?.category }} ·
                        Draw {{ store.activeTournament.draw_data?.draw_size }}
                    </div>
                </div>
                <div class="banner-right">
                    <span v-if="isOpen && !deadlinePassed" class="deadline-badge">
                        ⏱ Closes {{ formatDeadline(store.activeTournament.predictions_close_at) }}
                    </span>
                    <span v-else-if="isPredictionsClosed" class="deadline-badge closed">
                        🔒 Predictions closed
                    </span>
                    <span
                        class="status-badge"
                        :class="store.activeTournament.status"
                    >
                        {{ store.activeTournament.status.toUpperCase() }}
                    </span>
                </div>
            </div>

            <!-- Tabs -->
            <div class="tabs">
                <button
                    class="tab"
                    :class="{ active: activeTab === 'prediction' }"
                    @click="activeTab = 'prediction'"
                >🎯 My Prediction</button>
                <button
                    class="tab"
                    :class="{ active: activeTab === 'draw' }"
                    @click="activeTab = 'draw'"
                >🗺️ Tournament Draw</button>
                <button
                    class="tab"
                    :class="{ active: activeTab === 'leaderboard' }"
                    @click="activeTab = 'leaderboard'"
                >🏆 Leaderboard <span class="count">{{ store.entries.length }}</span></button>
                <button
                    class="tab"
                    :class="{ active: activeTab === 'all' }"
                    @click="activeTab = 'all'"
                >📋 All Predictions</button>
            </div>

            <!-- Tab content -->
            <div class="tab-content">

                <!-- My Prediction tab -->
                <div v-if="activeTab === 'prediction'">
                    <div v-if="!store.activeTournament.draw_data?.matches?.length" class="empty">
                        Draw not yet available.
                    </div>
                    <template v-else>
                        <ScoringLegend :draw="store.activeTournament.draw_data" />

                        <!-- Already submitted -->
                        <div v-if="alreadySubmitted" class="submitted-notice">
                            ✓ You have submitted your prediction for this tournament.
                        </div>

                        <!-- Qualifying bracket (only if draw has qualifying matches) -->
                        <div
                            v-if="hasQualifyingMatches"
                            class="bracket-section"
                        >
                            <h3 class="section-heading">Qualifications</h3>
                            <BracketEditor
                                :draw-data="store.activeTournament.draw_data"
                                :picks="alreadySubmitted ? (store.entries.find(e => e.nickname === store.myNickname)?.picks ?? store.myPicks) : store.myPicks"
                                :readonly="alreadySubmitted || !canSubmit"
                                section="qualifying"
                                @pick="handlePick"
                            />
                        </div>

                        <!-- Main bracket -->
                        <div class="bracket-section">
                            <h3 class="section-heading">Main Draw</h3>
                            <BracketEditor
                                :draw-data="store.activeTournament.draw_data"
                                :picks="alreadySubmitted ? (store.entries.find(e => e.nickname === store.myNickname)?.picks ?? store.myPicks) : store.myPicks"
                                :readonly="alreadySubmitted || !canSubmit"
                                section="main"
                                @pick="handlePick"
                            />
                        </div>

                        <!-- Submit bar -->
                        <div v-if="canSubmit && !submitSuccess" class="submit-bar">
                            <div v-if="submitError" class="submit-error">{{ submitError }}</div>
                            <div class="submit-row">
                                <input
                                    v-model="nicknameInput"
                                    class="nick-input"
                                    placeholder="Your nickname"
                                    maxlength="30"
                                    @keyup.enter="handleSubmit"
                                />
                                <button
                                    class="submit-btn"
                                    :disabled="store.loading"
                                    @click="handleSubmit"
                                >
                                    {{ store.loading ? 'Submitting...' : 'Submit Prediction →' }}
                                </button>
                            </div>
                            <div class="submit-hint">One submission per IP. Cannot be changed after submit.</div>
                        </div>

                        <div v-if="submitSuccess" class="success-notice">
                            🎉 Prediction submitted! Check the leaderboard tab.
                        </div>
                    </template>
                </div>

                <!-- Tournament Draw tab (read-only actual draw + results) -->
                <div v-if="activeTab === 'draw'">
                    <div v-if="!store.activeTournament.draw_data?.matches?.length" class="empty">
                        Draw not yet available.
                    </div>
                    <template v-else>
                        <div v-if="hasQualifyingMatches" class="bracket-section">
                            <h3 class="section-heading">Qualifications</h3>
                            <BracketEditor
                                :draw-data="store.activeTournament.draw_data"
                                :picks="actualPicks"
                                :readonly="true"
                                section="qualifying"
                                @pick="() => {}"
                            />
                        </div>
                        <div class="bracket-section">
                            <h3 class="section-heading">Main Draw</h3>
                            <BracketEditor
                                :draw-data="store.activeTournament.draw_data"
                                :picks="actualPicks"
                                :readonly="true"
                                section="main"
                                @pick="() => {}"
                            />
                        </div>
                    </template>
                </div>

                <!-- Leaderboard tab -->
                <div v-if="activeTab === 'leaderboard'">
                    <ScoringLegend :draw="store.activeTournament.draw_data" />
                    <PredictionLeaderboard
                        :entries="store.entries"
                        :tournament="store.activeTournament"
                        :my-nickname="store.myNickname"
                    />
                </div>

                <!-- All predictions tab -->
                <div v-if="activeTab === 'all'">
                    <AllPredictions
                        :entries="store.entries"
                        :draw-data="store.activeTournament.draw_data ?? null"
                        :tournament-id="store.activeTournament.id"
                    />
                </div>
            </div>
        </div>

        <!-- No active tournament -->
        <div v-else-if="!store.loading" class="no-tournament">
            <p>No active tournament at the moment. Check the archive below.</p>
        </div>

        <!-- Archive -->
        <div v-if="pastTournaments.length" class="archive-section">
            <h2 class="archive-title">Past Tournaments</h2>
            <div class="archive-grid">
                <div
                    v-for="t in pastTournaments"
                    :key="t.id"
                    class="archive-card"
                >
                    <div class="archive-name">{{ t.name }}</div>
                    <div class="archive-meta">{{ new Date(t.created_at).getFullYear() }}</div>
                    <div class="archive-entries">{{ t.entry_count }} predictions</div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.prediction-view { min-height: 100%; display: flex; flex-direction: column; gap: var(--space-6); }
.page-header h1 { font-size: var(--font-size-3xl); font-weight: var(--font-weight-bold); color: var(--color-text-primary); margin-bottom: var(--space-2); }
.intro { color: var(--color-text-secondary); font-size: var(--font-size-base); }

/* Banner */
.tournament-banner {
    display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: var(--space-3);
    background: var(--color-surface); border: 1px solid var(--color-border);
    border-radius: var(--radius-lg); padding: var(--space-4) var(--space-5);
    margin-bottom: var(--space-4);
}
.trn-name { font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); color: var(--color-text-primary); }
.trn-meta { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: var(--space-1); }
.banner-right { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.deadline-badge { font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); color: var(--color-warning); background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); padding: var(--space-1) var(--space-3); border-radius: var(--radius-full); }
.deadline-badge.closed { color: var(--color-text-muted); background: var(--color-bg-secondary); border-color: var(--color-border); }
.status-badge { font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); padding: var(--space-1) var(--space-3); border-radius: var(--radius-full); text-transform: uppercase; letter-spacing: 0.5px; }
.status-badge.open { background: rgba(34,197,94,0.1); color: var(--color-brand-live); border: 1px solid rgba(34,197,94,0.2); }
.status-badge.closed { background: var(--color-bg-secondary); color: var(--color-text-muted); border: 1px solid var(--color-border); }
.status-badge.finished { background: rgba(245,158,11,0.1); color: var(--color-warning); border: 1px solid rgba(245,158,11,0.3); }

/* Tabs */
.tabs { display: flex; gap: var(--space-1); border-bottom: 2px solid var(--color-border); padding-bottom: 0; margin-bottom: var(--space-4); }
.tab { padding: var(--space-2) var(--space-4); font-size: var(--font-size-sm); font-weight: var(--font-weight-medium); color: var(--color-text-secondary); background: transparent; border: none; border-bottom: 2px solid transparent; cursor: pointer; margin-bottom: -2px; transition: all var(--transition-fast); display: flex; align-items: center; gap: var(--space-2); }
.tab:hover { color: var(--color-text-primary); }
.tab.active { color: var(--color-accent); border-bottom-color: var(--color-accent); }
.count { font-size: var(--font-size-xs); background: var(--color-bg-secondary); padding: 1px 6px; border-radius: var(--radius-full); color: var(--color-text-muted); }

.tab-content { animation: fadeIn 0.15s ease-out; }
@keyframes fadeIn { from{opacity:0;transform:translateY(4px)} to{opacity:1;transform:none} }

/* Bracket */
.bracket-section { overflow-x: auto; margin-bottom: var(--space-4); }
.section-heading { font-size: var(--font-size-base); font-weight: var(--font-weight-semibold); color: var(--color-text-secondary); margin-bottom: var(--space-3); }

/* Submit bar */
.submit-bar { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-4); margin-top: var(--space-4); }
.submit-error { background: var(--color-error-light); border: 1px solid var(--color-error-border); border-radius: var(--radius-md); padding: var(--space-2) var(--space-3); color: var(--color-error); font-size: var(--font-size-sm); margin-bottom: var(--space-3); }
.submit-row { display: flex; gap: var(--space-3); align-items: center; }
.nick-input { flex: 1; background: var(--color-bg-secondary); border: 1px solid var(--color-border); border-radius: var(--radius-md); color: var(--color-text-primary); font-size: var(--font-size-sm); padding: var(--space-2) var(--space-3); outline: none; }
.nick-input:focus { border-color: var(--color-accent); }
.submit-btn { background: var(--color-accent); color: var(--color-text-inverse); font-weight: var(--font-weight-bold); font-size: var(--font-size-sm); padding: var(--space-2) var(--space-5); border-radius: var(--radius-md); border: none; cursor: pointer; white-space: nowrap; }
.submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.submit-hint { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-top: var(--space-2); }

/* Notices */
.submitted-notice, .success-notice {
    background: var(--color-success-light); border: 1px solid var(--color-success-border);
    border-radius: var(--radius-md); padding: var(--space-3) var(--space-4);
    color: var(--color-success); font-size: var(--font-size-sm); margin-bottom: var(--space-4);
}
.no-tournament { color: var(--color-text-muted); font-size: var(--font-size-sm); padding: var(--space-6) 0; }
.empty { color: var(--color-text-muted); font-size: var(--font-size-sm); text-align: center; padding: var(--space-8); }

/* Archive */
.archive-section { padding-top: var(--space-6); border-top: 1px solid var(--color-border); }
.archive-title { font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); color: var(--color-text-primary); margin-bottom: var(--space-4); }
.archive-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--space-3); }
.archive-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-4); transition: border-color var(--transition-fast); }
.archive-card:hover { border-color: var(--color-accent); }
.archive-name { font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin-bottom: var(--space-1); }
.archive-meta { font-size: var(--font-size-sm); color: var(--color-text-muted); }
.archive-entries { font-size: var(--font-size-xs); color: var(--color-text-muted); margin-top: var(--space-2); }
</style>
