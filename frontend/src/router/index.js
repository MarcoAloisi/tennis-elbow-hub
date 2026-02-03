import { createRouter, createWebHistory } from 'vue-router'
import LiveScoresView from '../views/LiveScoresView.vue'
import MatchAnalysisView from '../views/MatchAnalysisView.vue'
import WTSLTourLogsView from '../views/WTSLTourLogsView.vue'
import OnlineToursView from '../views/OnlineToursView.vue'
import GuidesView from '../views/GuidesView.vue'

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
    },
    {
        path: '/tour-logs',
        name: 'WTSLTourLogs',
        component: WTSLTourLogsView,
        meta: {
            title: 'WTSL Tour Logs'
        }
    },
    {
        path: '/online-tours',
        name: 'OnlineTours',
        component: OnlineToursView,
        redirect: '/online-tours/xkt',
        meta: {
            title: 'Online Tours'
        },
        children: [
            {
                path: 'xkt',
                name: 'XKTTour',
                component: OnlineToursView,
                meta: { title: 'XKT Tour' }
            },
            {
                path: 'wtsl',
                name: 'WTSLTour',
                component: OnlineToursView,
                meta: { title: 'WTSL Tour' }
            }
        ]
    },
    {
        path: '/guides',
        name: 'Guides',
        component: GuidesView,
        meta: {
            title: 'Guides'
        }
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// Update page title on navigation
router.beforeEach((to, from, next) => {
    document.title = `${to.meta.title || 'Tennis Elbow Hub'} | Tennis Elbow Hub`
    next()
})

export default router

