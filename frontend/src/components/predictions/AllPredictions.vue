<!-- frontend/src/components/predictions/AllPredictions.vue -->
<script setup lang="ts">
import { ref, computed } from 'vue'
import {
    usePredictionsStore,
    type PredictionEntry,
    type DrawData,
    type EntryBreakdown,
    type MatchBreakdownItem,
} from '@/stores/predictions'
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
const breakdown = ref<EntryBreakdown | null>(null)
const breakdownLoading = ref(false)
const breakdownError = ref<string | null>(null)

const ROUND_ORDER = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Qualified',
    'R1', 'R2', 'R3', 'R4', 'QF', 'SF', 'F']
const ROUND_LABELS: Record<string, string> = {
    Q1: 'Q1', Q2: 'Q2', Q3: 'Q3', Q4: 'Q4', Q5: 'Q5', Q6: 'Q6', Qualified: 'Qualified',
    R1: 'Round 1', R2: 'Round 2', R3: 'Round 3', R4: 'Round 4',
    QF: 'Quarterfinal', SF: 'Semifinal', F: 'Final',
}

const breakdownByRound = computed(() => {
    const items = breakdown.value?.items ?? []
    const map: Record<string, MatchBreakdownItem[]> = {}
    for (const it of items) {
        if (!it.predicted_winner) continue  // hide matches with no pick
        (map[it.round] ??= []).push(it)
    }
    return map
})

const roundsInBreakdown = computed(() =>
    ROUND_ORDER.filter(r => (breakdownByRound.value[r] ?? []).length)
)

const breakdownPointsEarned = computed(() =>
    (breakdown.value?.items ?? []).filter(it => it.points > 0).length
)

async function openEntry(entry: PredictionEntry) {
    viewingEntry.value = entry
    breakdown.value = null
    breakdownError.value = null
    breakdownLoading.value = true
    try {
        breakdown.value = await store.fetchBreakdown(props.tournamentId, entry.id)
    } catch (err: any) {
        breakdownError.value = err.message
    } finally {
        breakdownLoading.value = false
    }
}
function closeEntry() {
    viewingEntry.value = null
    breakdown.value = null
}

async function removeEntry(entry: PredictionEntry) {
    if (!confirm(`Remove prediction by "${entry.nickname}"?`)) return
    try {
        await store.deleteEntry(entry.id)
    } catch (err: any) {
        alert(err.message)
    }
}

function formatPick(item: MatchBreakdownItem): string {
    const parts: string[] = [item.predicted_winner ?? '—']
    if (item.predicted_retirement) parts.push('retired')
    else if (item.predicted_sets) parts.push(`${item.predicted_sets} sets`)
    return parts.join(' · ')
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

            <div class="detail-layout">
                <div v-if="drawData" class="detail-bracket">
                    <div
                        v-if="drawData.matches.some(m => m.section === 'qualifying')"
                        class="bracket-section"
                    >
                        <h4 class="mini-heading">Qualifications</h4>
                        <BracketEditor
                            :draw-data="drawData"
                            :picks="viewingEntry.picks"
                            :readonly="true"
                            section="qualifying"
                            @pick="() => {}"
                        />
                    </div>
                    <div class="bracket-section">
                        <h4 class="mini-heading">Main Draw</h4>
                        <BracketEditor
                            :draw-data="drawData"
                            :picks="viewingEntry.picks"
                            :readonly="true"
                            section="main"
                            @pick="() => {}"
                        />
                    </div>
                </div>

                <div class="breakdown-panel">
                    <div class="breakdown-header">
                        <span>Score breakdown</span>
                        <span v-if="breakdown" class="breakdown-meta">
                            {{ breakdownPointsEarned }} / {{ (breakdown?.items.filter(i => i.predicted_winner).length ?? 0) }} picks scored
                        </span>
                    </div>
                    <div v-if="breakdownLoading" class="breakdown-state">Loading…</div>
                    <div v-else-if="breakdownError" class="breakdown-state error">{{ breakdownError }}</div>
                    <div v-else-if="!roundsInBreakdown.length" class="breakdown-state">
                        No picks yet.
                    </div>
                    <div v-else class="breakdown-rounds">
                        <div v-for="round in roundsInBreakdown" :key="round" class="bd-round">
                            <div class="bd-round-header">
                                <span class="bd-round-label">{{ ROUND_LABELS[round] ?? round }}</span>
                            </div>
                            <div
                                v-for="item in breakdownByRound[round]"
                                :key="item.match_id"
                                class="bd-item"
                                :class="{
                                    win: item.points > 0,
                                    loss: item.points === 0 && item.actual_winner && item.actual_winner !== item.predicted_winner,
                                    pending: !item.actual_winner,
                                }"
                            >
                                <div class="bd-row">
                                    <span class="bd-pick">{{ formatPick(item) }}</span>
                                    <span class="bd-pts">+{{ item.points }}</span>
                                </div>
                                <div class="bd-reason">{{ item.reason }}<span v-if="item.actual_score" class="bd-actual"> · {{ item.actual_score }}</span></div>
                            </div>
                        </div>
                    </div>
                </div>
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

.detail-layout { display: grid; grid-template-columns: 1fr; gap: var(--space-4); }
@media (min-width: 1100px) {
    .detail-layout { grid-template-columns: minmax(0, 1fr) 340px; }
}
.detail-bracket { overflow-x: auto; display: flex; flex-direction: column; gap: var(--space-4); }
.mini-heading { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); color: var(--color-text-secondary); margin-bottom: var(--space-2); }
.bracket-section { overflow-x: auto; }

.breakdown-panel {
    background: var(--color-surface); border: 1px solid var(--color-border);
    border-radius: var(--radius-md); padding: var(--space-3);
    max-height: 70vh; overflow-y: auto;
}
.breakdown-header {
    display: flex; justify-content: space-between; align-items: center;
    font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary); margin-bottom: var(--space-2);
    padding-bottom: var(--space-2); border-bottom: 1px solid var(--color-border);
}
.breakdown-meta { font-size: var(--font-size-xs); color: var(--color-text-muted); font-weight: var(--font-weight-normal); }
.breakdown-state { color: var(--color-text-muted); font-size: var(--font-size-sm); padding: var(--space-3); text-align: center; }
.breakdown-state.error { color: var(--color-error); }

.breakdown-rounds { display: flex; flex-direction: column; gap: var(--space-3); }
.bd-round-header {
    font-size: var(--font-size-xs); font-weight: var(--font-weight-bold);
    color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.bd-item {
    border-left: 2px solid var(--color-border);
    padding: 4px 0 4px 8px; margin-bottom: 4px; font-size: var(--font-size-xs);
}
.bd-item.win { border-left-color: var(--color-brand-live); }
.bd-item.loss { border-left-color: var(--color-error); opacity: 0.75; }
.bd-item.pending { border-left-color: var(--color-border); }
.bd-row { display: flex; justify-content: space-between; align-items: center; gap: var(--space-2); color: var(--color-text-primary); }
.bd-pick { font-weight: var(--font-weight-medium); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bd-pts { font-family: var(--font-mono); font-weight: var(--font-weight-bold); color: var(--color-accent); min-width: 36px; text-align: right; }
.bd-item.loss .bd-pts { color: var(--color-text-muted); }
.bd-reason { color: var(--color-text-muted); font-size: 10px; margin-top: 2px; }
.bd-actual { font-family: var(--font-mono); }
</style>
