<!-- frontend/src/components/predictions/AdminPanel.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { usePredictionsStore, type Tournament } from '@/stores/predictions'

const props = defineProps<{
    tournament: Tournament | null
}>()

const emit = defineEmits<{ refresh: [] }>()

const store = usePredictionsStore()
const newUrl = ref('')
const newCloseAt = ref('')
const adminError = ref<string | null>(null)
const adminLoading = ref(false)

async function run(fn: () => Promise<void>) {
    adminLoading.value = true
    adminError.value = null
    try {
        await fn()
        emit('refresh')
    } catch (err: any) {
        adminError.value = err.message
    } finally {
        adminLoading.value = false
    }
}

async function create() {
    if (!newUrl.value || !newCloseAt.value) {
        adminError.value = 'URL and deadline are required'
        return
    }
    await run(async () => { await store.createTournament(newUrl.value, new Date(newCloseAt.value).toISOString()) })
    newUrl.value = ''
    newCloseAt.value = ''
}
</script>

<template>
    <div class="admin-panel">
        <div class="admin-header">⚙ Admin Panel</div>

        <div v-if="adminError" class="admin-error">{{ adminError }}</div>

        <!-- Create new tournament -->
        <div class="admin-section">
            <div class="section-title">Add Tournament</div>
            <input
                v-model="newUrl"
                class="admin-input"
                placeholder="https://www.managames.com/Forum/OT_ViewTournament.php?Trn=2045"
            />
            <div class="input-row">
                <input v-model="newCloseAt" class="admin-input" type="datetime-local" />
                <button class="admin-btn primary" :disabled="adminLoading" @click="create">
                    {{ adminLoading ? 'Creating...' : 'Publish Tournament' }}
                </button>
            </div>
        </div>

        <!-- Tournament controls -->
        <div v-if="tournament" class="admin-section">
            <div class="section-title">Manage: {{ tournament.name }}</div>
            <div class="btn-row">
                <button
                    class="admin-btn"
                    :disabled="adminLoading"
                    @click="run(() => store.refreshResults(tournament!.id))"
                >
                    🔄 Refresh Results
                </button>
                <button
                    v-if="tournament.status === 'open'"
                    class="admin-btn warning"
                    :disabled="adminLoading"
                    @click="run(() => store.closePredictions(tournament!.id))"
                >
                    🔒 Close Predictions
                </button>
                <button
                    v-if="tournament.status !== 'finished'"
                    class="admin-btn danger"
                    :disabled="adminLoading"
                    @click="run(() => store.markFinished(tournament!.id))"
                >
                    🏁 Mark Finished
                </button>
                <button
                    class="admin-btn danger"
                    :disabled="adminLoading"
                    @click="run(() => store.deleteTournament(tournament!.id))"
                >
                    🗑 Delete Tournament
                </button>
            </div>
        </div>
    </div>
</template>

<style scoped>
.admin-panel {
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-4);
    margin-bottom: var(--space-4);
}
.admin-header { font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: var(--space-3); }
.admin-error { background: var(--color-error-light); border: 1px solid var(--color-error-border); border-radius: var(--radius-md); padding: var(--space-2) var(--space-3); color: var(--color-error); font-size: var(--font-size-sm); margin-bottom: var(--space-3); }
.admin-section { margin-bottom: var(--space-4); }
.admin-section:last-child { margin-bottom: 0; }
.section-title { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); color: var(--color-text-secondary); margin-bottom: var(--space-2); }
.admin-input {
    width: 100%; background: var(--color-surface); border: 1px solid var(--color-border);
    border-radius: var(--radius-md); color: var(--color-text-primary); font-size: var(--font-size-sm);
    padding: var(--space-2) var(--space-3); outline: none; margin-bottom: var(--space-2);
}
.admin-input:focus { border-color: var(--color-accent); }
.input-row { display: flex; gap: var(--space-2); }
.input-row .admin-input { margin-bottom: 0; }
.btn-row { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.admin-btn {
    padding: var(--space-2) var(--space-3); border-radius: var(--radius-md); font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium); cursor: pointer; border: 1px solid var(--color-border);
    background: var(--color-surface); color: var(--color-text-primary); transition: all var(--transition-fast);
}
.admin-btn:hover { border-color: var(--color-accent); color: var(--color-accent); }
.admin-btn.primary { background: var(--color-accent); color: var(--color-text-inverse); border-color: var(--color-accent); }
.admin-btn.primary:hover { background: var(--color-accent-hover); }
.admin-btn.warning { border-color: var(--color-warning); color: var(--color-warning); }
.admin-btn.warning:hover { background: var(--color-warning-light); }
.admin-btn.danger { border-color: var(--color-error); color: var(--color-error); }
.admin-btn.danger:hover { background: var(--color-error-light); }
.admin-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
