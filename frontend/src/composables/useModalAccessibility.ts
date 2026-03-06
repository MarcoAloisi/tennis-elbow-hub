/**
 * Focus trap and Escape key composable for modals
 * Traps keyboard focus inside a modal element and handles Escape key to close.
 */
import { watch, nextTick, onUnmounted } from 'vue'

const FOCUSABLE_SELECTORS = [
    'a[href]',
    'button:not([disabled])',
    'textarea:not([disabled])',
    'input:not([disabled]):not([type="hidden"])',
    'select:not([disabled])',
    '[tabindex]:not([tabindex="-1"])'
].join(', ')

/**
 * @param {import('vue').Ref<boolean>} isOpen - Reactive ref controlling modal visibility
 * @param {Object} options
 * @param {Function} options.onClose - Callback when Escape is pressed or focus trap requests close
 * @param {string} options.containerSelector - CSS selector for the modal container (default: '[role="dialog"]')
 */
export function useModalAccessibility(isOpen: import('vue').Ref<boolean>, { onClose, containerSelector = '[role="dialog"]' }: { onClose?: () => void, containerSelector?: string } = {}) {
    let previousActiveElement: HTMLElement | Element | null = null

    function getFocusableElements(container: Element) {
        return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS))
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            event.preventDefault()
            onClose?.()
            return
        }

        if (event.key !== 'Tab') return

        const container = document.querySelector(containerSelector)
        if (!container) return

        const focusable = getFocusableElements(container)
        if (focusable.length === 0) return

        const firstElement = focusable[0]
        const lastElement = focusable[focusable.length - 1]

        if (event.shiftKey) {
            // Shift+Tab: if on first element, wrap to last
            if (document.activeElement === firstElement) {
                event.preventDefault()
                lastElement.focus()
            }
        } else {
            // Tab: if on last element, wrap to first
            if (document.activeElement === lastElement) {
                event.preventDefault()
                firstElement.focus()
            }
        }
    }

    function activate() {
        previousActiveElement = document.activeElement
        document.addEventListener('keydown', handleKeyDown)

        // Focus the first focusable element inside the modal
        nextTick(() => {
            const container = document.querySelector(containerSelector)
            if (!container) return
            const focusable = getFocusableElements(container)
            if (focusable.length > 0) {
                focusable[0].focus()
            }
        })
    }

    function deactivate() {
        document.removeEventListener('keydown', handleKeyDown)
        // Restore focus to the element that was focused before the modal opened
        if (previousActiveElement && typeof (previousActiveElement as HTMLElement).focus === 'function') {
            (previousActiveElement as HTMLElement).focus()
        }
        previousActiveElement = null
    }

    watch(isOpen, (newVal) => {
        if (newVal) {
            activate()
        } else {
            deactivate()
        }
    }, { immediate: true })

    onUnmounted(deactivate)

    return { activate, deactivate }
}
