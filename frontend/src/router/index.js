import { createRouter, createWebHistory } from 'vue-router'
import LiveScoresView from '../views/LiveScoresView.vue'
import MatchAnalysisView from '../views/MatchAnalysisView.vue'

const routes = [
    {
        path: '/',
        name: 'LiveScores',
        component: LiveScoresView,
        meta: {
            title: 'Live Scores'
        }
    },
    {
        path: '/analysis',
        name: 'MatchAnalysis',
        component: MatchAnalysisView,
        meta: {
            title: 'Match Analysis'
        }
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// Update page title on navigation
router.beforeEach((to, from, next) => {
    document.title = `${to.meta.title || 'Tennis Tracker'} | Tennis Tracker`
    next()
})

export default router
