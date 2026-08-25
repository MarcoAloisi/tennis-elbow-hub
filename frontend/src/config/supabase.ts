import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string

/**
 * Navigator LockManager throws in Firefox when another tab already holds the
 * auth-token lock (`ifAvailable` fails). Run the critical section anyway so
 * getSession / token refresh don't surface as an uncaught promise.
 */
async function authLock<R>(
    _name: string,
    acquireTimeout: number,
    fn: () => Promise<R>
): Promise<R> {
    if (typeof navigator === 'undefined' || !navigator.locks?.request) {
        return fn()
    }

    try {
        const ifAvailable = acquireTimeout === 0
        return await navigator.locks.request(
            _name,
            { mode: 'exclusive', ifAvailable },
            async (lock) => {
                if (!lock) return fn()
                return fn()
            }
        )
    } catch {
        return fn()
    }
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
    auth: { lock: authLock },
})

