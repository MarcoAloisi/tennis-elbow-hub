import { computed } from 'vue'

export function useMatchStats(store: any) {
    function mapStatsToStructure(s: any) {
        if (!s) return null
        return {
            serve: {
                first_serve_pct: s.first_serve_pct,
                aces: s.aces,
                double_faults: s.double_faults,
                fastest_serve_kmh: s.fastest_serve_kmh || s.fastest_serve,
                avg_first_serve_kmh: s.avg_first_serve_kmh || s.avg_first_serve,
                avg_second_serve_kmh: s.avg_second_serve_kmh || s.avg_second_serve,
                first_serve_in: s.first_serve_in,
                first_serve_total: s.first_serve_total
            },
            rally: {
                short_rallies_won: s.short_rallies_won,
                short_rallies_total: s.short_rallies_total,
                normal_rallies_won: s.normal_rallies_won,
                normal_rallies_total: s.normal_rallies_total,
                long_rallies_won: s.long_rallies_won,
                long_rallies_total: s.long_rallies_total,
                avg_rally_length: s.avg_rally_length
            },
            points: {
                winners: s.winners,
                forced_errors: s.forced_errors,
                unforced_errors: s.unforced_errors,
                points_on_first_serve_won: s.points_on_first_serve_won,
                points_on_first_serve_total: s.points_on_first_serve_total,
                points_on_second_serve_won: s.points_on_second_serve_won,
                points_on_second_serve_total: s.points_on_second_serve_total,
                return_points_won: s.return_points_won,
                return_points_total: s.return_points_total,
                return_winners: s.return_winners,
                net_points_won: s.net_points_won,
                net_points_total: s.net_points_total,
                total_points_won: s.total_points_won
            },
            break_points: {
                break_points_won: s.break_points_won,
                break_points_total: s.break_points_total,
                break_games_won: s.break_games_won,
                break_games_total: s.break_games_total,
                set_points_saved: s.set_points_saved,
                match_points_saved: s.match_points_saved
            },
            general: {
                elo_diff: s.elo_change
            }
        }
    }

    const aggregatedPlayerStats = computed(() => {
        return mapStatsToStructure(store.aggregateStats)
    })

    const aggregatedOpponentStats = computed(() => {
        return mapStatsToStructure(store.aggregateStats?.opponent)
    })

    // Get color class for percentage values based on ranges
    function getPercentClass(value: number | string) {
        const num = typeof value === 'string' ? parseFloat(value) : value
        if (isNaN(num)) return ''
        if (num <= 30) return 'pct-danger'       // 0-30%: red
        if (num < 50) return 'pct-warning'       // 31-49%: orange
        if (num <= 60) return 'pct-neutral'      // 50-60%: default/black
        if (num < 90) return 'pct-good'          // 61-89%: green
        return 'pct-excellent'                   // 90%+: neon yellow
    }

    return {
        mapStatsToStructure,
        aggregatedPlayerStats,
        aggregatedOpponentStats,
        getPercentClass
    }
}
