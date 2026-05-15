import React, { useEffect, useState } from 'react'
import { API_URL } from '../config'

function Holdings() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_URL}/api/holdings`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))

    const iv = setInterval(() => {
      fetch(`${API_URL}/api/holdings`).then(r => r.json()).then(setData).catch(() => {})
    }, 30000)
    return () => clearInterval(iv)
  }, [])

  if (loading) return <div className="text-center py-20 text-slate-400">Loading Company Holdings...</div>
  if (!data) return <div className="text-center py-20 text-slate-400">No holdings data.</div>

  const holdings = data.holdings || []
  const cash = data.cash || 0
  const totalValue = data.total_value || 0
  const totalReturnPct = data.total_return_pct || 0
  const openPositions = data.open_positions || 0
  const closedTrades = data.closed_trades || 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Company Holdings</h2>
          <p className="text-sm text-slate-400">Live paper portfolio — SCC Command Center</p>
        </div>
        <div className="px-3 py-1 rounded text-xs font-bold bg-emerald-600 text-white">
          {openPositions} Open / {closedTrades} Closed
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
          <div className="text-xs text-slate-400 uppercase tracking-wider">Cash</div>
          <div className="text-xl font-mono font-bold">${cash.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
          <div className="text-xs text-slate-400 uppercase tracking-wider">Total Value</div>
          <div className="text-xl font-mono font-bold">${totalValue.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
          <div className="text-xs text-slate-400 uppercase tracking-wider">Total Return</div>
          <div className={`text-xl font-mono font-bold ${totalReturnPct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {totalReturnPct >= 0 ? '+' : ''}{totalReturnPct}%
          </div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
          <div className="text-xs text-slate-400 uppercase tracking-wider">Initial Capital</div>
          <div className="text-xl font-mono font-bold">${(data.initial_capital || 100000).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
        </div>
      </div>

      {/* Positions Table */}
      {holdings.length === 0 ? (
        <div className="text-center py-12 text-slate-500 bg-slate-800/50 rounded-xl border border-dashed border-slate-700">
          No open positions. The bot is scanning for its next trade...
        </div>
      ) : (
        <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-900/60 text-slate-300 text-left">
                <th className="px-4 py-3 font-semibold">Ticker</th>
                <th className="px-4 py-3 font-semibold text-right">Shares</th>
                <th className="px-4 py-3 font-semibold text-right">Entry</th>
                <th className="px-4 py-3 font-semibold text-right">Last Price</th>
                <th className="px-4 py-3 font-semibold text-right">Value</th>
                <th className="px-4 py-3 font-semibold text-right">Unrealized PnL</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {holdings.map(h => {
                const pnl = h.unrealized_pnl || 0
                const pct = h.unrealized_pnl_pct || 0
                const isProfit = pnl >= 0
                return (
                  <tr key={h.ticker} className="hover:bg-slate-700/30 transition">
                    <td className="px-4 py-3 font-bold">{h.ticker}</td>
                    <td className="px-4 py-3 text-right font-mono">{h.shares}</td>
                    <td className="px-4 py-3 text-right font-mono">${h.entry_price}</td>
                    <td className="px-4 py-3 text-right font-mono">${h.last_price}</td>
                    <td className="px-4 py-3 text-right font-mono">${(h.value_usd || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                    <td className={`px-4 py-3 text-right font-mono font-semibold ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {isProfit ? '+' : ''}${(pnl).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                      <span className="text-xs ml-1 opacity-70">({isProfit ? '+' : ''}{pct}%)</span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default Holdings
