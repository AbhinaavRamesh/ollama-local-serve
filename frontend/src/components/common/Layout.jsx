/**
 * Main layout wrapper component.
 */

import { Outlet } from 'react-router-dom'
import Header from './Header'
import ErrorBoundary from './ErrorBoundary'

/**
 * Main application layout.
 */
export function Layout() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <Header />
      <main className="container mx-auto px-4 py-6">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
      <footer className="border-t border-slate-200 dark:border-slate-700 py-4 mt-auto">
        <div className="container mx-auto px-4 text-center text-sm text-slate-500 dark:text-slate-400">
          Ollama Monitor &middot; Built with React &amp; TailwindCSS
        </div>
      </footer>
    </div>
  )
}

export default Layout
