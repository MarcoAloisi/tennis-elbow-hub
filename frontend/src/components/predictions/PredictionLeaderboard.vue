<!-- frontend/src/components/predictions/PredictionLeaderboard.vue -->
<script setup lang="ts">
import { computed } from 'vue'
import type { PredictionEntry, Tournament } from '@/stores/predictions'

const props = defineProps<{
    entries: PredictionEntry[]
    tournament: Tournament
    myNickname: string
}>()

const isFinished = computed(() => props.tournament.status === 'finished')

const maxScore = computed(() => props.entries[0]?.total_score ?? 1)

function barWidth(score: number): string {
    return `${Math.round((score / Math.max(maxScore.value, 1)) * 100)}%`
}

const top3 = computed(() => props.entries.slice(0, 3))
</script>

<template>
    <div class="leaderboard">
        <!-- Podium (only when finished) -->
        <div v-if="isFinished && top3.length" class="podium-wrap">
            <div class="podium-title">Prediction Champions</div>
            <div class="podium">
                <!-- 2nd -->
                <div v-if="top3[1]" class="podium-slot">
                    <div class="avatar silver">{{ top3[1].nickname[0].toUpperCase() }}</div>
                    <div class="podium-name">{{ top3[1].nickname }}</div>
                    <div class="podium-score silver-text">{{ top3[1].total_score }} pts</div>
                    <div class="podium-block silver-block">2</div>
                </div>
                <!-- 1st -->
                <div class="podium-slot">
                    <div class="avatar gold">{{ top3[0].nickname[0].toUpperCase() }}</div>
                    <div class="podium-name">{{ top3[0].nickname }}</div>
                    <div class="podium-score gold-text">{{ top3[0].total_score }} pts</div>
                    <div class="podium-block gold-block">1</div>
                </div>
                <!-- 3rd -->
                <div v-if="top3[2]" class="podium-slot">
                    <div class="avatar bronze">{{ top3[2].nickname[0].toUpperCase() }}</div>
                    <div class="podium-name">{{ top3[2].nickname }}</div>
                    <div class="podium-score bronze-text">{{ top3[2].total_score }} pts</div>
                    <div class="podium-block bronze-block">3</div>
                </div>
            </div>
        </div>

        <!-- Live badge -->
        <div v-if="!isFinished" class="live-badge">
            <span class="live-dot" />
            In progress · scores update when admin refreshes results
        </div>

        <!-- Rankings table -->
        <div v-if="entries.length === 0" class="empty">No predictions yet.</div>
        <div v-else class="rows">
            <div
                v-for="(entry, i) in entries"
                :key="entry.id"
                class="lb-row"
                :class="{
                    'rank-1': i === 0,
                    'is-me': entry.nickname === myNickname,
                }"
            >
                <span class="rank" :class="{ gold: i === 0, silver: i === 1, bronze: i === 2 }">
                    {{ i + 1 }}
                </span>
                <span class="nick">
                    {{ entry.nickname }}
                    <span v-if="entry.nickname === myNickname" class="me-tag">YOU</span>
                </span>
                <div class="bar-wrap">
                    <div class="bar" :style="{ width: barWidth(entry.total_score) }" />
                </div>
                <span class="score">{{ entry.total_score }}</span>
            </div>
        </div>
    </div>
</template>

<style scoped>
.leaderboard { display: flex; flex-direction: column; gap: var(--space-4); }

/* Podium */
.podium-title {
    text-align: center; font-size: var(--font-size-sm); font-weight: var(--font-weight-bold);
    text-transform: uppercase; letter-spacing: 1px; color: var(--color-text-secondary);
    margin-bottom: var(--space-4);
}
.podium { display: flex; align-items: flex-end; justify-content: center; gap: var(--space-2); padding-bottom: var(--space-4); border-bottom: 1px solid var(--color-border); }
.podium-slot { display: flex; flex-direction: column; align-items: center; gap: var(--space-1); }
.avatar {
    width: 40px; height: 40px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: var(--font-size-base); font-weight: var(--font-weight-bold);
    border: 2px solid;
}
.avatar.gold { background: rgba(245,158,11,0.12); border-color: var(--color-warning); color: var(--color-warning); }
.avatar.silver { background: rgba(148,163,184,0.1); border-color: #94A3B8; color: #94A3B8; }
.avatar.bronze { background: rgba(180,83,9,0.1); border-color: #b45309; color: #b45309; }
.podium-name { font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); max-width: 80px; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.podium-score { font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); padding: 2px 7px; border-radius: var(--radius-full); font-family: var(--font-mono); }
.gold-text { color: var(--color-warning); background: rgba(245,158,11,0.12); }
.silver-text { color: #94A3B8; background: rgba(148,163,184,0.08); }
.bronze-text { color: #b45309; background: rgba(180,83,9,0.08); }
.podium-block { border-radius: 6px 6px 0 0; display: flex; align-items: center; justify-content: center; font-size: var(--font-size-xl); font-weight: var(--font-weight-bold); color: var(--color-bg-primary); }
.gold-block { width: 84px; height: 90px; background: linear-gradient(160deg, var(--color-warning), #92400e); }
.silver-block { width: 74px; height: 68px; background: linear-gradient(160deg, #94A3B8, #475569); }
.bronze-block { width: 74px; height: 52px; background: linear-gradient(160deg, #b45309, #292524); }

/* Live badge */
.live-badge {
    display: inline-flex; align-items: center; gap: var(--space-2);
    font-size: var(--font-size-xs); color: var(--color-brand-live);
    background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.2);
    padding: var(--space-1) var(--space-3); border-radius: var(--radius-full);
    width: fit-content;
}
.live-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--color-brand-live); animation: pulse 1.5s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

.empty { color: var(--color-text-muted); font-size: var(--font-size-sm); text-align: center; padding: var(--space-8); }

/* Rows */
.rows { display: flex; flex-direction: column; gap: var(--space-2); }
.lb-row {
    display: flex; align-items: center; gap: var(--space-3);
    padding: var(--space-2) var(--space-3);
    background: var(--color-surface); border: 1px solid var(--color-border);
    border-radius: var(--radius-md); font-size: var(--font-size-sm);
    transition: border-color var(--transition-fast);
}
.lb-row.rank-1 { border-color: var(--color-warning); background: rgba(245,158,11,0.04); }
.lb-row.is-me { border-color: var(--color-accent); background: var(--color-accent-light); }
.rank { font-weight: var(--font-weight-bold); min-width: 20px; color: var(--color-text-muted); font-size: var(--font-size-xs); }
.rank.gold { color: var(--color-warning); }
.rank.silver { color: #94A3B8; }
.rank.bronze { color: #b45309; }
.nick { flex: 1; color: var(--color-text-primary); font-weight: var(--font-weight-medium); display: flex; align-items: center; gap: var(--space-2); }
.me-tag { font-size: var(--font-size-xs); color: var(--color-accent); border: 1px solid var(--color-accent); padding: 1px 5px; border-radius: var(--radius-sm); font-weight: var(--font-weight-bold); }
.bar-wrap { width: 80px; height: 3px; background: var(--color-border); border-radius: 2px; overflow: hidden; flex-shrink: 0; }
.bar { height: 100%; background: var(--color-accent); border-radius: 2px; }
.lb-row.rank-1 .bar { background: var(--color-warning); }
.score { font-family: var(--font-mono); font-weight: var(--font-weight-bold); color: var(--color-accent); font-size: var(--font-size-sm); min-width: 45px; text-align: right; }
.lb-row.rank-1 .score { color: var(--color-warning); }
</style>
