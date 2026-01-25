/**
 * Pinia store for match analysis
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiUrl } from '@/config/api'

export const useAnalysisStore = defineStore('analysis', () => {
    // State
    const currentAnalysis = ref(null)
    const analysisHistory = ref([])
    const isLoading = ref(false)
    const error = ref(null)
    const uploadProgress = ref(0)

    // Getters
    const hasAnalysis = computed(() => currentAnalysis.value !== null)

    const player1Stats = computed(() => currentAnalysis.value?.stats?.player1 || null)
    const player2Stats = computed(() => currentAnalysis.value?.stats?.player2 || null)
    const matchInfo = computed(() => currentAnalysis.value?.stats?.info || null)

    // Actions
    async function uploadAndAnalyze(file) {
        isLoading.value = true
        error.value = null
        uploadProgress.value = 0

        try {
            const formData = new FormData()
            formData.append('file', file)

            const response = await fetch(apiUrl('/api/analysis/upload'), {
                method: 'POST',
                body: formData
            })

            uploadProgress.value = 100

            if (!response.ok) {
                const errorData = await response.json()
                throw new Error(errorData.detail || `HTTP error ${response.status}`)
            }

            const data = await response.json()

            if (data.success) {
                currentAnalysis.value = data
                // Add to history
                analysisHistory.value.unshift({
                    ...data,
                    uploadedAt: new Date().toISOString()
                })
                // Keep only last 10 analyses
                if (analysisHistory.value.length > 10) {
                    analysisHistory.value.pop()
                }
            } else {
                throw new Error(data.error || 'Analysis failed')
            }

            return data
        } catch (e) {
            error.value = e.message
            console.error('Failed to analyze file:', e)
            throw e
        } finally {
            isLoading.value = false
        }
    }

    async function loadSampleAnalysis() {
        isLoading.value = true
        error.value = null

        try {
            const response = await fetch(apiUrl('/api/analysis/sample'))

            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`)
            }

            const data = await response.json()
            currentAnalysis.value = data
            return data
        } catch (e) {
            error.value = e.message
            console.error('Failed to load sample:', e)
            throw e
        } finally {
            isLoading.value = false
        }
    }

    function clearAnalysis() {
        currentAnalysis.value = null
        error.value = null
    }

    function loadFromHistory(index) {
        if (analysisHistory.value[index]) {
            currentAnalysis.value = analysisHistory.value[index]
        }
    }

    return {
        // State
        currentAnalysis,
        analysisHistory,
        isLoading,
        error,
        uploadProgress,
        // Getters
        hasAnalysis,
        player1Stats,
        player2Stats,
        matchInfo,
        // Actions
        uploadAndAnalyze,
        loadSampleAnalysis,
        clearAnalysis,
        loadFromHistory
    }
})
