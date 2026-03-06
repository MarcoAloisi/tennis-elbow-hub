import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiUrl } from '@/config/api'

export const useGuidesStore = defineStore('guides', () => {
    const guides = ref<any[]>([])
    const currentGuide = ref<any | null>(null)
    const tags = ref<string[]>([])
    const loading = ref<boolean>(false)
    const error = ref<string | null>(null)
    const pagination = ref({
        total: 0,
        page: 1,
        pageSize: 12,
        totalPages: 1
    })

    interface FetchGuidesParams {
        tag?: string;
        type?: string;
        search?: string;
        page?: number;
        pageSize?: number;
    }

    async function fetchGuides({ tag = '', type = '', search = '', page = 1, pageSize = 12 }: FetchGuidesParams = {}) {
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
        } catch (err: any) {
            error.value = err.message
            console.error('Failed to fetch guides:', err)
        } finally {
            loading.value = false
        }
    }

    async function fetchGuide(slug: string) {
        loading.value = true
        error.value = null
        currentGuide.value = null
        try {
            const response = await fetch(apiUrl(`/api/guides/${slug}`))
            if (!response.ok) {
                throw new Error(`Error fetching guide: ${response.statusText}`)
            }
            currentGuide.value = await response.json()
        } catch (err: any) {
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

    async function createGuide(formData: FormData, token: string) {
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
        } catch (err: any) {
            error.value = err.message
            console.error('Failed to create guide:', err)
            throw err
        } finally {
            loading.value = false
        }
    }

    async function updateGuide(guideId: number | string, formData: FormData, token: string) {
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
            const index = guides.value.findIndex((g: any) => g.id === guideId)
            if (index !== -1) {
                guides.value[index] = updatedGuide
            }
            await fetchTags()
            return updatedGuide
        } catch (err: any) {
            error.value = err.message
            console.error('Failed to update guide:', err)
            throw err
        } finally {
            loading.value = false
        }
    }

    async function deleteGuide(guideId: number | string, token: string) {
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

            guides.value = guides.value.filter((g: any) => g.id !== guideId)
            pagination.value.total = Math.max(0, pagination.value.total - 1)
        } catch (err) {
            console.error('Failed to delete guide:', err)
            throw err
        }
    }

    function clearError() {
        error.value = null
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
        deleteGuide,
        clearError
    }
})
