import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiUrl } from '@/config/api'

export const useGuidesStore = defineStore('guides', () => {
    const guides = ref([])
    const currentGuide = ref(null)
    const tags = ref([])
    const loading = ref(false)
    const error = ref(null)
    const pagination = ref({
        total: 0,
        page: 1,
        pageSize: 12,
        totalPages: 1
    })

    async function fetchGuides({ tag = '', type = '', search = '', page = 1, pageSize = 12 } = {}) {
        loading.value = true
        error.value = null
        try {
            const params = new URLSearchParams()
            if (tag && tag.toLowerCase() !== 'all') params.set('tag', tag)
            if (type) params.set('type', type)
            if (search) params.set('search', search)
            params.set('page', String(page))
            params.set('page_size', String(pageSize))

            const response = await fetch(apiUrl(`/api/guides?${params.toString()}`))
            if (!response.ok) {
                throw new Error(`Error fetching guides: ${response.statusText}`)
            }
            const data = await response.json()
            guides.value = data.items
            pagination.value = {
                total: data.total,
                page: data.page,
                pageSize: data.page_size,
                totalPages: data.total_pages
            }
        } catch (err) {
            error.value = err.message
            console.error('Failed to fetch guides:', err)
        } finally {
            loading.value = false
        }
    }

    async function fetchGuide(slug) {
        loading.value = true
        error.value = null
        currentGuide.value = null
        try {
            const response = await fetch(apiUrl(`/api/guides/${slug}`))
            if (!response.ok) {
                throw new Error(`Error fetching guide: ${response.statusText}`)
            }
            currentGuide.value = await response.json()
        } catch (err) {
            error.value = err.message
            console.error('Failed to fetch guide:', err)
        } finally {
            loading.value = false
        }
    }

    async function fetchTags() {
        try {
            const response = await fetch(apiUrl('/api/guides/tags'))
            if (!response.ok) {
                throw new Error(`Error fetching tags: ${response.statusText}`)
            }
            tags.value = await response.json()
        } catch (err) {
            console.error('Failed to fetch tags:', err)
        }
    }

    async function createGuide(formData, token) {
        loading.value = true
        error.value = null
        try {
            const response = await fetch(apiUrl('/api/guides'), {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            })

            if (!response.ok) {
                const errData = await response.json()
                throw new Error(errData.detail || `Error creating guide: ${response.statusText}`)
            }

            const newGuide = await response.json()
            await fetchTags()
            return newGuide
        } catch (err) {
            error.value = err.message
            console.error('Failed to create guide:', err)
            throw err
        } finally {
            loading.value = false
        }
    }

    async function updateGuide(guideId, formData, token) {
        loading.value = true
        error.value = null
        try {
            const response = await fetch(apiUrl(`/api/guides/${guideId}`), {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            })

            if (!response.ok) {
                const errData = await response.json()
                throw new Error(errData.detail || `Error updating guide: ${response.statusText}`)
            }

            const updatedGuide = await response.json()
            const index = guides.value.findIndex(g => g.id === guideId)
            if (index !== -1) {
                guides.value[index] = updatedGuide
            }
            await fetchTags()
            return updatedGuide
        } catch (err) {
            error.value = err.message
            console.error('Failed to update guide:', err)
            throw err
        } finally {
            loading.value = false
        }
    }

    async function deleteGuide(guideId, token) {
        try {
            const response = await fetch(apiUrl(`/api/guides/${guideId}`), {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            if (!response.ok) {
                const errData = await response.json()
                throw new Error(errData.detail || `Error deleting guide: ${response.statusText}`)
            }

            guides.value = guides.value.filter(g => g.id !== guideId)
            pagination.value.total = Math.max(0, pagination.value.total - 1)
        } catch (err) {
            console.error('Failed to delete guide:', err)
            throw err
        }
    }

    return {
        guides,
        currentGuide,
        tags,
        loading,
        error,
        pagination,
        fetchGuides,
        fetchGuide,
        fetchTags,
        createGuide,
        updateGuide,
        deleteGuide
    }
})
