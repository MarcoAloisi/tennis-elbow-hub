import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiUrl } from '@/config/api'

export const useOutfitsStore = defineStore('outfits', () => {
    const outfits = ref([])
    const loading = ref(false)
    const error = ref(null)

    async function fetchOutfits(category = 'All') {
        loading.value = true
        error.value = null
        try {
            let path = '/api/outfits'
            if (category && category !== 'All') {
                path += `?category=${category}`
            }

            const url = apiUrl(path)
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
            const response = await fetch(apiUrl('/api/outfits'), {
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

    async function updateOutfit(outfitId, formData, token) {
        loading.value = true
        error.value = null
        try {
            const response = await fetch(apiUrl(`/api/outfits/${outfitId}`), {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            })

            if (!response.ok) {
                const errData = await response.json()
                throw new Error(errData.detail || `Error updating outfit: ${response.statusText}`)
            }

            const updatedOutfit = await response.json()
            // Find and update the outfit in the local array
            const index = outfits.value.findIndex(o => o.id === outfitId)
            if (index !== -1) {
                outfits.value[index] = updatedOutfit
            }
            return updatedOutfit
        } catch (err) {
            error.value = err.message
            console.error('Failed to update outfit:', err)
            throw err
        } finally {
            loading.value = false
        }
    }

    async function deleteOutfit(outfitId, token) {
        try {
            const response = await fetch(apiUrl(`/api/outfits/${outfitId}`), {
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
        updateOutfit,
        deleteOutfit
    }
})
