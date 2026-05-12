import React, { useState } from 'react'
import { API_URL } from '../config'

function Settings() {
  const [triggering, setTriggering] = useState(false)
  const [triggerMsg, setTriggerMsg] = useState('')

  const triggerCycle = async () => {
    setTriggering(true)
    setTriggerMsg('Running cycle...')
    try {
      const r = await fetch(`${API_URL}/api/trigger-cycle`, { method: 'POST' })
      const d = await r.json()
      setTriggerMsg(`Status: ${d.status} — ${d.message}`)
    } catch (e) {
      setTriggerMsg(`Error: ${e.message}`)
    } finally {
      setTriggering(false)
    }
  }

  return (
    <div className="space-y-6 max-w-xl">
      <h2 className="text-xl font-bold">Settings</h2>

      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 space-y-4">
        <h3 className="text-sm uppercase tracking-wide text-slate-400">Actions</h3>
        <button
          onClick={triggerCycle}
          disabled={triggering}
          className="bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white px-4 py-2 rounded text-sm font-semibold transition"
        >
          {triggering ? 'Running...' : 'Run One Cycle Now'}
        </button>
        {triggerMsg && <p className="text-sm text-slate-300 mt-2">{triggerMsg}</p>}
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 space-y-3">
        <h3 className="text-sm uppercase tracking-wide text-slate-400">API Status</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span>FastAPI Backend</span>
            <span className="text-green-400">● Connected</span>
          </div>
          <div className="flex justify-between">
            <span>yfinance</span>
            <span className="text-yellow-400">● Standby</span>
          </div>
          <div className="flex justify-between">
            <span>CoinGecko</span>
            <span className="text-yellow-400">● Standby</span>
          </div>
        </div>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h3 className="text-sm uppercase tracking-wide text-slate-400 mb-2">About</h3>
        <p className="text-sm text-slate-300">
          Stock Command Center v1.0 — Autonomous research platform with paper trading.
          Runs 24/7 cron cycles. All data backed up to GitHub.
        </p>
      </div>
    </div>
  )
}

export default Settings
