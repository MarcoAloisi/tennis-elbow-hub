import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useOutfitsStore = defineStore('outfits', () => {
    const outfits = ref([])
    const loading = ref(false)
    const error = ref(null)

    // API base URL
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

    async function fetchOutfits(category = 'All') {
        loading.value = true
        error.value = null
        try {
            let url = `${API_URL}/outfits`
            if (category && category !== 'All') {
                url += `?category=${category}`
            }

            const response = await fetch(url)
            if (!response.ok) {
                throw new Error(`Error fetching outfits: ${response.statusText}`)
            }
            outfits.value = await response.json()
        } catch (err) {
            error.value = err.message
            console.error('Failed to fetch outfits:', err)
        } finally {
            loading.value = false
        }
    }

    async function createOutfit(formData, token) {
        loading.value = true
        error.value = null
        try {
            const response = await fetch(`${API_URL}/outfits`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData // sending as FormData because it contains a file
            })

            if (!response.ok) {
                const errData = await response.json()
                throw new Error(errData.detail || `Error creating outfit: ${response.statusText}`)
            }

            const newOutfit = await response.json()
            // Prepend to array
            outfits.value.unshift(newOutfit)
            return newOutfit
        } catch (err) {
            error.value = err.message
            console.error('Failed to create outfit:', err)
            throw err
        } finally {
            loading.value = false
        }
    }

    async function deleteOutfit(outfitId, token) {
        try {
            const response = await fetch(`${API_URL}/outfits/${outfitId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            if (!response.ok) {
                const errData = await response.json()
                throw new Error(errData.detail || `Error deleting outfit: ${response.statusText}`)
            }

            outfits.value = outfits.value.filter(o => o.id !== outfitId)
        } catch (err) {
            console.error('Failed to delete outfit:', err)
            throw err
        }
    }

    return {
        outfits,
        loading,
        error,
        fetchOutfits,
        createOutfit,
        deleteOutfit
    }
})
