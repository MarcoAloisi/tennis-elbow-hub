/**
 * API configuration for production/development
 */

// API base URL - uses environment variable in production, proxy in development
export const API_BASE_URL = typeof __API_URL__ !== 'undefined' && __API_URL__
    ? __API_URL__
    : ''

// WebSocket URL
export const WS_BASE_URL = API_BASE_URL
    ? API_BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://')
    : ''

/**
 * Build full API URL
 */
export function apiUrl(path) {
    return `${API_BASE_URL}${path}`
}

/**
 * Build full WebSocket URL
 */
export function wsUrl(path) {
    if (WS_BASE_URL) {
        return `${WS_BASE_URL}${path}`
    }
    // Fallback for development - use relative path for proxy
    return path
}
