import { createRouter, createWebHistory } from 'vue-router'
import LiveScoresView from '../views/LiveScoresView.vue'
import MatchAnalysisView from '../views/MatchAnalysisView.vue'
import WTSLTourLogsView from '../views/WTSLTourLogsView.vue'
import OnlineToursView from '../views/OnlineToursView.vue'
import GuidesView from '../views/GuidesView.vue'
import AboutView from '../views/AboutView.vue'
import PrivacyPolicyView from '../views/PrivacyPolicyView.vue'

const routes = [
    {
        path: '/',
        name: 'Home',
        component: AboutView,
        meta: {
            title: 'Home',
            description: 'Tennis Elbow Hub — the community hub for Tennis Elbow 4 players. Live scores, match analysis, online tours, and video guides.'
        }
    },
    {
        path: '/live',
        name: 'LiveScores',
        component: LiveScoresView,
        meta: {
            title: 'Live Scores',
            description: 'Live Tennis Elbow 4 match scores updated in real-time. Track online matches, ELO ratings, and daily statistics.'
        }
    },
    {
        path: '/analysis',
        name: 'MatchAnalysis',
        component: MatchAnalysisView,
        meta: {
            title: 'Match Analysis',
            description: 'Upload and analyze Tennis Elbow 4 match logs. Radar charts, head-to-head stats, win rates, and detailed performance metrics.'
        }
    },
    {
        path: '/tour-logs',
        name: 'WTSLTourLogs',
        component: WTSLTourLogsView,
        meta: {
            title: 'WTSL Tour Logs',
            description: 'Analyze WTSL tour CSV files with player rankings, statistical leaders, and complete match history.'
        }
    },
    {
        path: '/online-tours',
        name: 'OnlineTours',
        component: OnlineToursView,
        redirect: '/online-tours/xkt',
        meta: {
            title: 'Online Tours',
            description: 'Browse online Tennis Elbow 4 tours including XKT and WTSL. Tournament info, rules, and community links.'
        },
        children: [
            {
                path: 'xkt',
                name: 'XKTTour',
                component: OnlineToursView,
                meta: {
                    title: 'XKT Tour',
                    description: 'XKT Tour for Tennis Elbow 4 — competitive online tournament with seasonal rankings and structured play.'
                }
            },
            {
                path: 'wtsl',
                name: 'WTSLTour',
                component: OnlineToursView,
                meta: {
                    title: 'WTSL Tour',
                    description: 'WTSL Tour for Tennis Elbow 4 — online competitive tour with ELO rankings and match statistics.'
                }
            }
        ]
    },
    {
        path: '/guides',
        name: 'Guides',
        component: GuidesView,
        meta: {
            title: 'Guides',
            description: 'Video tutorials and guides for Tennis Elbow 4 online play. Setup, gameplay tips, and tournament guides.'
        }
    },
    {
        path: '/privacy-policy',
        name: 'PrivacyPolicy',
        component: PrivacyPolicyView,
        meta: {
            title: 'Privacy Policy',
            description: 'Tennis Elbow Hub privacy policy. Information about cookies, analytics, and data collection.'
        }
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes,
    scrollBehavior() {
        return { top: 0 }
    }
})

// Update page title and meta description on navigation
router.beforeEach((to, from, next) => {
    document.title = `${to.meta.title || 'Tennis Elbow Hub'} | Tennis Elbow Hub`

    const descriptionMeta = document.querySelector('meta[name="description"]')
    if (descriptionMeta && to.meta.description) {
        descriptionMeta.setAttribute('content', to.meta.description)
    }

    next()
})

export default router

