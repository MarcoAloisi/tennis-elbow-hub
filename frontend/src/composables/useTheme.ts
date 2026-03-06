/**
 * Theme composable for managing dark/light mode
 * Initializes synchronously to prevent flash of wrong theme.
 */
import { ref, computed, watch } from 'vue'

const THEME_KEY = 'tennis-tracker-theme'

// Synchronous initialization — runs once at module load, before any component mounts
function getInitialTheme() {
    try {
        const saved = localStorage.getItem(THEME_KEY)
        if (saved === 'light' || saved === 'dark') return saved
    } catch { /* localStorage unavailable */ }
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark'
    }
    return 'dark'
}

// Theme state — shared across all component instances
const theme = ref(getInitialTheme())

// Apply immediately so the DOM matches before first paint
if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', theme.value)
}

export function useTheme() {
    /**
     * Toggle between light and dark theme
     */
    function toggleTheme() {
        theme.value = theme.value === 'light' ? 'dark' : 'light'
    }

    /**
     * Set a specific theme
     */
    function setTheme(newTheme) {
        theme.value = newTheme
    }

    /**
     * Reactive check for dark mode
     */
    const isDark = computed(() => theme.value === 'dark')

    // Watch for theme changes and update DOM + localStorage
    watch(theme, (newTheme) => {
        document.documentElement.setAttribute('data-theme', newTheme)
        try {
            localStorage.setItem(THEME_KEY, newTheme)
        } catch { /* localStorage unavailable */ }
    })

    return {
        theme,
        toggleTheme,
        setTheme,
        isDark
    }
}
