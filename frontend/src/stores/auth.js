import { defineStore } from 'pinia'
import { ref } from 'vue'
import { supabase } from '@/config/supabase'

export const useAuthStore = defineStore('auth', () => {
    const user = ref(null)
    const session = ref(null)
    const loading = ref(true)
    const error = ref(null)

    // Initialize Auth state from Supabase
    const initAuth = async () => {
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
        } catch (err) {
            console.error('Error initializing auth:', err.message)
            error.value = err.message
        } finally {
            loading.value = false
        }
    }

    const register = async (email, password, displayName) => {
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
        } catch (err) {
            error.value = err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    const login = async (email, password) => {
        loading.value = true
        error.value = null
        try {
            const { data, error: signInError } = await supabase.auth.signInWithPassword({
                email,
                password
            })
            if (signInError) throw signInError
            return data
        } catch (err) {
            error.value = err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    const logout = async () => {
        loading.value = true
        error.value = null
        try {
            const { error: signOutError } = await supabase.auth.signOut()
            if (signOutError) throw signOutError

            user.value = null
            session.value = null
        } catch (err) {
            error.value = err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    const updateDisplayName = async (newName) => {
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
        } catch (err) {
            error.value = err.message
            console.error('Failed to update display name:', err)
            throw err
        } finally {
            loading.value = false
        }
    }

    return {
        user,
        session,
        loading,
        error,
        initAuth,
        register,
        login,
        logout,
        updateDisplayName
    }
})
