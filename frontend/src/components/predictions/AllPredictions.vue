<!-- frontend/src/components/predictions/AllPredictions.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { usePredictionsStore, type PredictionEntry, type DrawData } from '@/stores/predictions'
import { useAuthStore } from '@/stores/auth'
import BracketEditor from './BracketEditor.vue'

const props = defineProps<{
    entries: PredictionEntry[]
    drawData: DrawData | null
    tournamentId: number
}>()

const store = usePredictionsStore()
const authStore = useAuthStore()
const viewingEntry = ref<PredictionEntry | null>(null)

function openEntry(entry: PredictionEntry) {
    viewingEntry.value = entry
}
function closeEntry() {
    viewingEntry.value = null
}

async function removeEntry(entry: PredictionEntry) {
    if (!confirm(`Remove prediction by "${entry.nickname}"?`)) return
    try {
        await store.deleteEntry(entry.id)
    } catch (err: any) {
        alert(err.message)
    }
}
</script>

<template>
    <div class="all-predictions">
        <!-- Detail view overlay -->
        <div v-if="viewingEntry" class="detail-overlay">
            <div class="detail-header">
                <button class="back-btn" @click="closeEntry">← Back</button>
                <span class="detail-title">{{ viewingEntry.nickname }}'s Prediction</span>
                <span class="detail-score">{{ viewingEntry.total_score }} pts</span>
            </div>
            <div v-if="drawData" class="detail-bracket">
                <BracketEditor
                    :draw-data="drawData"
                    :picks="viewingEntry.picks"
                    :readonly="true"
                    section="main"
                />
            </div>
        </div>

        <!-- Table -->
        <div v-else>
            <div v-if="entries.length === 0" class="empty">No predictions submitted yet.</div>
            <table v-else class="entries-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Nickname</th>
                        <th>Submitted</th>
                        <th>Score</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="(entry, i) in entries"
                        :key="entry.id"
                        class="entry-row"
                        @click="openEntry(entry)"
                    >
                        <td class="rank-col">{{ i + 1 }}</td>
                        <td class="nick-col">{{ entry.nickname }}</td>
                        <td class="date-col">{{ new Date(entry.submitted_at).toLocaleDateString() }}</td>
                        <td class="score-col">{{ entry.total_score }} pts</td>
                        <td class="actions-col" @click.stop>
                            <button
                                v-if="authStore.isAdmin"
                                class="del-btn"
                                @click="removeEntry(entry)"
                            >✕</button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<style scoped>
.all-predictions { display: flex; flex-direction: column; gap: var(--space-3); }
.empty { color: var(--color-text-muted); font-size: var(--font-size-sm); text-align: center; padding: var(--space-8); }

.entries-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.entries-table th { padding: var(--space-2) var(--space-3); text-align: left; font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--color-border); }
.entry-row { cursor: pointer; transition: background var(--transition-fast); }
.entry-row:hover td { background: var(--color-bg-hover); }
.entry-row td { padding: var(--space-3); border-bottom: 1px solid var(--color-border); color: var(--color-text-primary); }
.rank-col { color: var(--color-text-muted); width: 40px; }
.score-col { font-family: var(--font-mono); font-weight: var(--font-weight-bold); color: var(--color-accent); }
.date-col { color: var(--color-text-muted); }
.del-btn { background: none; border: 1px solid var(--color-border); color: var(--color-error); border-radius: var(--radius-sm); padding: 2px 7px; cursor: pointer; font-size: var(--font-size-xs); }
.del-btn:hover { background: var(--color-error-light); border-color: var(--color-error); }

/* Detail overlay */
.detail-overlay { display: flex; flex-direction: column; gap: var(--space-4); }
.detail-header { display: flex; align-items: center; gap: var(--space-4); padding-bottom: var(--space-3); border-bottom: 1px solid var(--color-border); }
.back-btn { background: none; border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-1) var(--space-3); color: var(--color-text-secondary); cursor: pointer; font-size: var(--font-size-sm); }
.back-btn:hover { border-color: var(--color-accent); color: var(--color-accent); }
.detail-title { flex: 1; font-weight: var(--font-weight-semibold); color: var(--color-text-primary); }
.detail-score { font-family: var(--font-mono); font-weight: var(--font-weight-bold); color: var(--color-accent); }
.detail-bracket { overflow-x: auto; }
</style>
