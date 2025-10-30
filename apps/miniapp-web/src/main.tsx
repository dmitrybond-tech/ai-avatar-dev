import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'
import { App } from './App'
import { getTelegramWebApp, isTelegramWebView } from './lib/tg'
import { postClientLog } from './api/client'

const rootEl = document.getElementById('root')!

function showSafeMode(message: string) {
  try {
    rootEl.innerHTML = ''
    const container = document.createElement('div')
    container.textContent = 'Miniapp failed to initialize inside Telegram. Retrying…'
    rootEl.appendChild(container)
  } catch {/* ignore */}
  try {
    if (isTelegramWebView()) {
      postClientLog({
        ua: typeof navigator !== 'undefined' ? navigator.userAgent : '',
        location: typeof window !== 'undefined' ? String(window.location) : '',
        message,
        stack: undefined,
      }).catch(()=>{})
    }
  } catch {/* ignore */}
}

window.addEventListener('error', (e) => {
  console.error('Global error:', e.error || e.message)
  showSafeMode(e?.error?.message || e.message || 'error')
})

window.addEventListener('unhandledrejection', (e: PromiseRejectionEvent) => {
  const msg = (e.reason && (e.reason.message || String(e.reason))) || 'unhandledrejection'
  const stack = e.reason && e.reason.stack ? String(e.reason.stack) : undefined
  console.error('Unhandled rejection:', e.reason)
  try {
    if (isTelegramWebView()) {
      postClientLog({
        ua: typeof navigator !== 'undefined' ? navigator.userAgent : '',
        location: typeof window !== 'undefined' ? String(window.location) : '',
        message: msg,
        stack,
      }).catch(()=>{})
    }
  } catch {/* ignore */}
  showSafeMode(msg)
})

try {
  // Guarded Telegram initialization
  getTelegramWebApp()
} catch (e) {
  console.warn('TG init failed', e)
}

ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
