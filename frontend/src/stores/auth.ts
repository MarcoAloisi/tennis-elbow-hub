import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { supabase } from '@/config/supabase'
import type { User, Session } from '@supabase/supabase-js'

export const useAuthStore = defineStore('auth', () => {
    const user = ref<User | null>(null)
    const session = ref<Session | null>(null)
    const loading = ref<boolean>(true)
    const error = ref<string | null>(null)

    // Role-based access: check app_metadata.role (tamper-proof, set server-side only)
    const isAdmin = computed(() => user.value?.app_metadata?.role === 'admin')

    // Initialize Auth state from Supabase
    const initAuth = async (): Promise<void> => {
        loading.value = true
        try {
            // Get initial session
            const { data: { session: initialSession }, error: sessionError } = await supabase.auth.getSession()

            if (sessionError) throw sessionError

            if (initialSession) {
                session.value = initialSession
                user.value = initialSession.user
            }

            // Listen for auth changes (login, logout, token refresh)
            supabase.auth.onAuthStateChange((_event, currentSession) => {
                session.value = currentSession
                user.value = currentSession?.user || null
            })
        } catch (err: any) {
            console.error('Error initializing auth:', err.message)
            error.value = err.message
        } finally {
            loading.value = false
        }
    }

    const register = async (email: string, password: string, displayName: string) => {
        loading.value = true
        error.value = null
        try {
            const { data, error: signUpError } = await supabase.auth.signUp({
                email,
                password,
                options: {
                    data: {
                        display_name: displayName
                    }
                }
            })
            if (signUpError) throw signUpError
            return data
        } catch (err: any) {
            error.value = err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    const login = async (email: string, password: string) => {
        loading.value = true
        error.value = null
        try {
            const { data, error: signInError } = await supabase.auth.signInWithPassword({
                email,
                password
            })
            if (signInError) throw signInError
            return data
        } catch (err: any) {
            error.value = err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    const logout = async (): Promise<void> => {
        loading.value = true
        error.value = null
        try {
            const { error: signOutError } = await supabase.auth.signOut()
            if (signOutError) throw signOutError

            user.value = null
            session.value = null
        } catch (err: any) {
            error.value = err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    const updateDisplayName = async (newName: string) => {
        loading.value = true
        error.value = null
        try {
            const { data, error: updateError } = await supabase.auth.updateUser({
                data: { display_name: newName }
            })
            if (updateError) throw updateError

            if (data?.user) {
                user.value = data.user
            }
            return data
        } catch (err: any) {
            error.value = err.message
            console.error('Failed to update display name:', err)
            throw err
        } finally {
            loading.value = false
        }
    }

    const resetPassword = async (email: string): Promise<void> => {
        loading.value = true
        error.value = null
        try {
            const { error: err } = await supabase.auth.resetPasswordForEmail(email, {
                redirectTo: `${window.location.origin}/reset-password`,
            })
            if (err) throw err
        } catch (e: any) {
            error.value = e.message || 'Failed to send reset email'
            throw e
        } finally {
            loading.value = false
        }
    }

    const updatePassword = async (newPassword: string): Promise<void> => {
        loading.value = true
        error.value = null
        try {
            const { error: err } = await supabase.auth.updateUser({ password: newPassword })
            if (err) throw err
        } catch (e: any) {
            error.value = e.message || 'Failed to update password'
            throw e
        } finally {
            loading.value = false
        }
    }

    function clearError(): void {
        error.value = null
    }

    return {
        user,
        session,
        loading,
        error,
        isAdmin,
        initAuth,
        register,
        login,
        logout,
        updateDisplayName,
        resetPassword,
        updatePassword,
        clearError
    }
})
