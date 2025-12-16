/**
 * Toast notification component using Sonner.
 */

import { Toaster, toast } from 'sonner'

/**
 * Toast container component.
 * Add this once at the app root.
 */
export function ToastProvider() {
  return (
    <Toaster
      position="bottom-right"
      toastOptions={{
        duration: 4000,
        className: 'sonner-toast',
        style: {
          background: 'hsl(var(--card))',
          color: 'hsl(var(--card-foreground))',
          border: '1px solid hsl(var(--border))',
        },
      }}
      closeButton
      richColors
    />
  )
}

/**
 * Show a success toast.
 * @param {string} message - Toast message
 * @param {Object} options - Additional options
 */
export function showSuccess(message, options = {}) {
  toast.success(message, options)
}

/**
 * Show an error toast.
 * @param {string} message - Toast message
 * @param {Object} options - Additional options
 */
export function showError(message, options = {}) {
  toast.error(message, options)
}

/**
 * Show an info toast.
 * @param {string} message - Toast message
 * @param {Object} options - Additional options
 */
export function showInfo(message, options = {}) {
  toast.info(message, options)
}

/**
 * Show a warning toast.
 * @param {string} message - Toast message
 * @param {Object} options - Additional options
 */
export function showWarning(message, options = {}) {
  toast.warning(message, options)
}

/**
 * Show a loading toast.
 * @param {string} message - Toast message
 * @returns {string|number} Toast ID for dismissing
 */
export function showLoading(message) {
  return toast.loading(message)
}

/**
 * Dismiss a toast.
 * @param {string|number} id - Toast ID
 */
export function dismissToast(id) {
  toast.dismiss(id)
}

/**
 * Show a promise toast (loading -> success/error).
 * @param {Promise} promise - The promise to track
 * @param {Object} messages - Messages for loading/success/error
 */
export function showPromise(promise, messages) {
  return toast.promise(promise, {
    loading: messages.loading || 'Loading...',
    success: messages.success || 'Success!',
    error: messages.error || 'Something went wrong',
  })
}

export { toast }
export default ToastProvider
