import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import AboutView from '../views/AboutView.vue'

// Lazy-loaded views — only downloaded when the route is navigated to
const LiveScoresView = () => import('../views/LiveScoresView.vue')
const MatchAnalysisView = () => import('../views/MatchAnalysisView.vue')
const WTSLTourLogsView = () => import('../views/WTSLTourLogsView.vue')
const OnlineToursView = () => import('../views/OnlineToursView.vue')
const GuidesView = () => import('../views/GuidesView.vue')
const PrivacyPolicyView = () => import('../views/PrivacyPolicyView.vue')
const TermsOfServiceView = () => import('../views/TermsOfServiceView.vue')
const ContactView = () => import('../views/ContactView.vue')
const OutfitGalleryView = () => import('../views/OutfitGalleryView.vue')
const LoginView = () => import('../views/LoginView.vue')
const AdminPlayersView = () => import('../views/AdminPlayersView.vue')
const AdminPanelView = () => import('../views/AdminPanelView.vue')
const PredictionView = () => import('../views/PredictionView.vue')

const SignupView = () => import('../views/SignupView.vue')
const ResetPasswordView = () => import('../views/ResetPasswordView.vue')
const ProfileView = () => import('../views/ProfileView.vue')
const PublicProfileView = () => import('../views/PublicProfileView.vue')
const PendingApprovalView = () => import('../views/PendingApprovalView.vue')

const routes: RouteRecordRaw[] = [
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
        path: '/login',
        name: 'Login',
        component: LoginView,
        meta: {
            title: 'Log In',
            description: 'Log in to your Tennis Elbow Hub account to upload and manage outfits.'
        }
    },
    {
        path: '/signup',
        name: 'Signup',
        component: SignupView,
        meta: {
            title: 'Sign Up',
            description: 'Create a new Tennis Elbow Hub account.'
        }
    },
    {
        path: '/pending-approval',
        name: 'PendingApproval',
        component: PendingApprovalView,
        meta: {
            title: 'Pending Approval',
            description: 'Your account is awaiting admin approval.',
            requiresAuth: true
        }
    },
    {
        path: '/reset-password',
        name: 'ResetPassword',
        component: ResetPasswordView,
        meta: {
            title: 'Reset Password',
            description: 'Reset your Tennis Elbow Hub account password.'
        }
    },
    {
        path: '/profile',
        name: 'Profile',
        component: ProfileView,
        meta: {
            title: 'Profile',
            description: 'View and edit your Tennis Elbow Hub profile.',
            requiresAuth: true
        }
    },
    {
        path: '/profile/:userId',
        name: 'PublicProfile',
        component: PublicProfileView,
        meta: {
            title: 'Profile',
            description: 'View player profile.',
            requiresAuth: true
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
        path: '/outfit-gallery',
        name: 'OutfitGallery',
        component: OutfitGalleryView,
        meta: {
            title: 'Outfit Code Gallery',
            description: 'Browse, preview, and copy player outfits for Tennis Elbow 4.'
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
            },
        ]
    },
    {
        path: '/online-tours/xkt/predictions',
        name: 'XKTPredictions',
        component: PredictionView,
        meta: {
            title: 'XKT Tournament Predictions',
            description: 'Predict XKT tournament bracket results and compete with other players.'
        }
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
        path: '/guides/:slug',
        name: 'GuideDetail',
        component: () => import('../views/GuideDetailView.vue'),
        meta: {
            title: 'Guide',
            description: 'Read guide on Tennis Elbow Hub.'
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
    },
    {
        path: '/terms-of-service',
        name: 'TermsOfService',
        component: TermsOfServiceView,
        meta: {
            title: 'Terms of Service',
            description: 'Tennis Elbow Hub terms of service. Usage rules, intellectual property, and legal information.'
        }
    },
    {
        path: '/contact',
        name: 'Contact',
        component: ContactView,
        meta: {
            title: 'Contact',
            description: 'Contact Tennis Elbow Hub. Send us a message with your name, Discord tag, and feedback.'
        }
    },
    {
        path: '/admin/players',
        name: 'AdminPlayers',
        component: AdminPlayersView,
        meta: {
            title: 'Players Database',
            description: 'Admin-only players database with ELO ratings and match history.',
            requiresAdmin: true
        }
    },
    {
        path: '/admin/panel',
        name: 'AdminPanel',
        component: AdminPanelView,
        meta: {
            title: 'Admin Panel',
            description: 'Admin panel for managing player link verifications.',
            requiresAdmin: true
        }
    }
]

// Cache approval status per user to avoid fetching on every navigation
let _approvalCache: { userId: string; approved: boolean } | null = null
export function clearApprovalCache() { _approvalCache = null }

const router = createRouter({
    history: createWebHistory(),
    routes,
    scrollBehavior() {
        return { top: 0 }
    }
})

// Update page title and meta description on navigation
router.beforeEach(async (to, from, next) => {
    document.title = `${to.meta.title || 'Tennis Elbow Hub'} | Tennis Elbow Hub`

    const descriptionMeta = document.querySelector('meta[name="description"]')
    if (descriptionMeta && to.meta.description) {
        descriptionMeta.setAttribute('content', to.meta.description as string)
    }

    // Auth route guard
    if (to.meta.requiresAuth) {
        const { useAuthStore } = await import('../stores/auth')
        const authStore = useAuthStore()
        if (!authStore.user) {
            return next('/login')
        }
    }

    // Admin route guard
    if (to.meta.requiresAdmin) {
        const { useAuthStore } = await import('../stores/auth')
        const authStore = useAuthStore()
        if (!authStore.isAdmin) {
            return next('/')
        }
    }

    // Approval guard: non-admin logged-in users must be approved
    const publicPaths = ['/login', '/signup', '/reset-password', '/pending-approval', '/privacy-policy', '/terms-of-service', '/contact', '/']
    if (!publicPaths.includes(to.path)) {
        const { useAuthStore } = await import('../stores/auth')
        const authStore = useAuthStore()
        if (authStore.user && !authStore.isAdmin) {
            const userId = authStore.user.id
            if (_approvalCache?.userId !== userId) {
                const { supabase } = await import('../config/supabase')
                const { apiUrl } = await import('../config/api')
                const { data } = await supabase.auth.getSession()
                if (data.session) {
                    const res = await fetch(apiUrl('/api/profile/me'), {
                        headers: { Authorization: `Bearer ${data.session.access_token}` },
                    })
                    if (res.ok) {
                        const profile = await res.json()
                        _approvalCache = { userId, approved: profile.approved }
                    }
                }
            }
            if (_approvalCache?.approved === false) {
                return next('/pending-approval')
            }
        }
    }

    next()
})

router.afterEach(() => {
    // Force scroll to top after route change to fix footer link bug
    window.scrollTo({ top: 0, behavior: 'instant' })
})

export default router

