/**
 * WebSocket composable for real-time data
 */
import { ref, onMounted, onUnmounted } from 'vue'

export function useWebSocket(url) {
    const data = ref(null)
    const isConnected = ref(false)
    const error = ref(null)
    const reconnectAttempts = ref(0)

    let socket = null
    let reconnectTimeout = null
    const MAX_RECONNECT_ATTEMPTS = 5
    const RECONNECT_DELAY = 3000

    /**
     * Connect to WebSocket server
     */
    function connect() {
        if (socket?.readyState === WebSocket.OPEN) {
            return
        }

        try {
            // Build WebSocket URL
            const wsUrl = url.startsWith('ws')
                ? url
                : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${url}`

            socket = new WebSocket(wsUrl)

            socket.onopen = () => {
                isConnected.value = true
                error.value = null
                reconnectAttempts.value = 0
                console.log('WebSocket connected')
            }

            socket.onmessage = (event) => {
                try {
                    data.value = JSON.parse(event.data)
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e)
                }
            }

            socket.onerror = (e) => {
                console.error('WebSocket error:', e)
                error.value = 'Connection error'
            }

            socket.onclose = () => {
                isConnected.value = false
                console.log('WebSocket disconnected')

                // Attempt reconnection
                if (reconnectAttempts.value < MAX_RECONNECT_ATTEMPTS) {
                    reconnectTimeout = setTimeout(() => {
                        reconnectAttempts.value++
                        console.log(`Reconnecting... (${reconnectAttempts.value}/${MAX_RECONNECT_ATTEMPTS})`)
                        connect()
                    }, RECONNECT_DELAY)
                } else {
                    error.value = 'Connection lost. Please refresh the page.'
                }
            }
        } catch (e) {
            error.value = 'Failed to connect'
            console.error('WebSocket connection failed:', e)
        }
    }

    /**
     * Disconnect from WebSocket server
     */
    function disconnect() {
        if (reconnectTimeout) {
            clearTimeout(reconnectTimeout)
        }
        if (socket) {
            socket.close()
            socket = null
        }
        isConnected.value = false
    }

    /**
     * Send a message through WebSocket
     */
    function send(message) {
        if (socket?.readyState === WebSocket.OPEN) {
            socket.send(typeof message === 'string' ? message : JSON.stringify(message))
        }
    }

    // Auto-connect on mount
    onMounted(() => {
        connect()
    })

    // Cleanup on unmount
    onUnmounted(() => {
        disconnect()
    })

    return {
        data,
        isConnected,
        error,
        reconnectAttempts,
        connect,
        disconnect,
        send
    }
}
