import React from 'react'
import ReactDOM from 'react-dom/client'
import './styles.css'
import { App } from './App'
import { safeInitTelegram } from './lib/telegram'
import { clientLog } from './lib/clientLog'

const rootEl = document.getElementById('root')!

// Initialize Telegram gracefully
const { tg, inTg } = safeInitTelegram()
clientLog("info", "miniapp_init", { inTg })

window.addEventListener('error', (e) => {
  console.error('Global error:', e.error || e.message)
  clientLog("error", e?.error?.message || e.message || 'error', {
    stack: e?.error?.stack,
  })
})

window.addEventListener('unhandledrejection', (e: PromiseRejectionEvent) => {
  const msg = (e.reason && (e.reason.message || String(e.reason))) || 'unhandledrejection'
  const stack = e.reason && e.reason.stack ? String(e.reason.stack) : undefined
  console.error('Unhandled rejection:', e.reason)
  clientLog("error", msg, { stack })
})

ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
