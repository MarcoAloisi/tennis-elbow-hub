/**
 * Theme composable for managing dark/light mode
 */
import { ref, watch, onMounted } from 'vue'

const THEME_KEY = 'tennis-tracker-theme'

// Theme state - shared across all component instances
const theme = ref('light')

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
     * Check if dark mode is active
     */
    const isDark = () => theme.value === 'dark'

    // Initialize theme from localStorage or system preference
    onMounted(() => {
        const savedTheme = localStorage.getItem(THEME_KEY)

        if (savedTheme) {
            theme.value = savedTheme
        } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            theme.value = 'dark'
        }
    })

    // Watch for theme changes and update DOM + localStorage
    watch(theme, (newTheme) => {
        document.documentElement.setAttribute('data-theme', newTheme)
        localStorage.setItem(THEME_KEY, newTheme)
    }, { immediate: true })

    return {
        theme,
        toggleTheme,
        setTheme,
        isDark
    }
}
