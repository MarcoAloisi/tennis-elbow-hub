import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiUrl } from '@/config/api'

export const useOutfitsStore = defineStore('outfits', () => {
    const outfits = ref([])
    const uploaders = ref([])
    const loading = ref(false)
    const error = ref(null)
    const pagination = ref({
        total: 0,
        page: 1,
        pageSize: 12,
        totalPages: 1
    })

    async function fetchOutfits({ search = '', uploader = '', category = 'All', page = 1, pageSize = 12 } = {}) {
        loading.value = true
        error.value = null
        try {
            const params = new URLSearchParams()
            if (category && category !== 'All') params.set('category', category)
            if (search) params.set('search', search)
            if (uploader) params.set('uploader', uploader)
            params.set('page', String(page))
            params.set('page_size', String(pageSize))

            const qs = params.toString()
            const url = apiUrl(`/api/outfits?${qs}`)
            const response = await fetch(url)
            if (!response.ok) {
                throw new Error(`Error fetching outfits: ${response.statusText}`)
            }
            const data = await response.json()
            outfits.value = data.items
            pagination.value = {
                total: data.total,
                page: data.page,
                pageSize: data.page_size,
                totalPages: data.total_pages
            }
        } catch (err) {
            error.value = err.message
            console.error('Failed to fetch outfits:', err)
        } finally {
            loading.value = false
        }
    }

    async function fetchUploaders() {
        try {
            const response = await fetch(apiUrl('/api/outfits/uploaders'))
            if (!response.ok) {
                throw new Error(`Error fetching uploaders: ${response.statusText}`)
            }
            uploaders.value = await response.json()
        } catch (err) {
            console.error('Failed to fetch uploaders:', err)
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
            // Re-fetch current page to stay in sync with server-side pagination
            // Also refresh uploaders in case this is a new uploader
            await fetchUploaders()
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
            // Update locally for immediate UI feedback
            const index = outfits.value.findIndex(o => o.id === outfitId)
            if (index !== -1) {
                outfits.value[index] = updatedOutfit
            }
            await fetchUploaders()
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
            pagination.value.total = Math.max(0, pagination.value.total - 1)
        } catch (err) {
            console.error('Failed to delete outfit:', err)
            throw err
        }
    }

    return {
        outfits,
        uploaders,
        loading,
        error,
        pagination,
        fetchOutfits,
        fetchUploaders,
        createOutfit,
        updateOutfit,
        deleteOutfit
    }
})
