import { onMounted, onUnmounted, ref } from 'vue'

/**
 * True only after adsbygoogle.js actually runs. Stays false when AdBlock /
 * Firefox tracking protection blocks the script, so the ad rails can hide
 * instead of showing empty skyscrapers.
 */
export function useAdSense() {
    const adsAllowed = ref(false)
    let pollId: ReturnType<typeof setInterval> | null = null

    function enableIfLoaded() {
        if ((window as unknown as { adsbygoogle?: { loaded?: boolean } }).adsbygoogle?.loaded) {
            adsAllowed.value = true
            if (pollId) {
                clearInterval(pollId)
                pollId = null
            }
            return true
        }
        return false
    }

    onMounted(() => {
        if (enableIfLoaded()) return

        const script = document.querySelector<HTMLScriptElement>(
            'script[src*="pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"]'
        )
        script?.addEventListener('load', enableIfLoaded)
        script?.addEventListener('error', () => {
            adsAllowed.value = false
        })

        pollId = setInterval(enableIfLoaded, 250)
        window.setTimeout(() => {
            if (pollId) {
                clearInterval(pollId)
                pollId = null
            }
        }, 4000)
    })

    onUnmounted(() => {
        if (pollId) clearInterval(pollId)
    })

    return { adsAllowed }
}
