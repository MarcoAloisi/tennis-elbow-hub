import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import { useAuthStore } from './auth'
import { wsUrl } from '@/config/api'

export const usePresenceStore = defineStore('presence', () => {
    const registeredCount = ref(0)
    const guestCount = ref(0)
    const authStore = useAuthStore()

    function buildUrl(): string {
        const token = authStore.session?.access_token
        return wsUrl(token ? `/api/presence/ws?token=${encodeURIComponent(token)}` : '/api/presence/ws')
    }

    // maxReconnectAttempts: Infinity — this connection represents the
    // visitor's whole session, unlike a page-scoped widget where giving up
    // after a few tries and telling the user to refresh is acceptable.
    const { data, isConnected, connect, disconnect } = useWebSocket(buildUrl, { maxReconnectAttempts: Infinity })

    watch(data, (message: any) => {
        if (!message) return
        if (typeof message.registered_count === 'number') registeredCount.value = message.registered_count
        if (typeof message.guest_count === 'number') guestCount.value = message.guest_count
    })

    // A tab that logs in or out mid-session must be re-classified without a
    // page reload: drop the old connection and reconnect with the new token
    // (or none). The very first connect — which happens before authStore's
    // initAuth() has necessarily resolved — will naturally be as a guest
    // and gets corrected here as soon as the real session loads.
    watch(
        () => authStore.session?.access_token,
        () => {
            disconnect()
            connect()
        }
    )

    return { registeredCount, guestCount, isConnected }
})
