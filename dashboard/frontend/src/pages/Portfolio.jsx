import React, { useEffect, useState } from 'react'
import { API_URL } from '../config'

function Portfolio() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_URL}/api/portfolio`)
      .then(r => r.json())
      .then(d => {
        setData(d)
        setLoading(false)
      })
      .catch(() => setLoading(false))

    const iv = setInterval(() => {
      fetch(`${API_URL}/api/portfolio`).then(r => r.json()).then(setData).catch(() => {})
    }, 30000)
    return () => clearInterval(iv)
  }, [])

  if (loading) return <div className="text-center py-20 text-slate-400">Loading Portfolio...</div>
  if (!data) return <div className="text-center py-20 text-slate-400">No portfolio data.</div>

  const market = data.market_status || {}
  const positions = Object.values(data.positions || {})
  const history = data.history || []

  const formatMoney = (n) => {
    if (n === undefined || n === null) return '-'
    return n.toLocaleString('en-US', {style: 'currency', currency: 'USD'})
  }

  const formatPct = (n) => {
    if (n === undefined || n === null) return '-'
    const color = n >= 0 ? 'text-green-400' : 'text-red-400'
    return <span className={color}>{n > 0 ? '+' : ''}{n.toFixed(2)}%</span>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Paper Trading Portfolio</h2>
          <p className="text-sm text-slate-400">Starting capital: {formatMoney(data.initial_capital || 100000)}</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`px-3 py-1 rounded text-xs font-bold ${market.open ? 'bg-green-600 text-white' : 'bg-red-600 text-white'}`}>
            {market.open ? 'MARKET OPEN' : 'MARKET CLOSED'}
          </div>
          <span className="text-xs text-slate-400">{market.et_time} ET — {market.reason}</span>
        </div>
      </div>

      {/* Top Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
          <div className="text-xs text-slate-400 uppercase">Total Value</div>
          <div className="text-2xl font-bold">{formatMoney(data.total_value)}</div>
          <div className="text-sm">{formatPct(data.total_return_pct)}</div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
          <div className="text-xs text-slate-400 uppercase">Cash</div>
          <div className="text-2xl font-bold">{formatMoney(data.cash)}</div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
          <div className="text-xs text-slate-400 uppercase">Realized P&L</div>
          <div className="text-2xl font-bold">{formatMoney(data.realized_pnl)}</div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
          <div className="text-xs text-slate-400 uppercase">Unrealized P&L</div>
          <div className="text-2xl font-bold">{formatMoney(data.unrealized_pnl)}</div>
        </div>
      </div>

      {/* Win Rate & Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-center">
          <div className="text-xs text-slate-400 uppercase">Win Rate</div>
          <div className="text-xl font-bold">{data.win_rate?.toFixed(1)}%</div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-center">
          <div className="text-xs text-slate-400 uppercase">Avg Return</div>
          <div className="text-xl font-bold">{data.avg_return_pct?.toFixed(2)}%</div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-center">
          <div className="text-xs text-slate-400 uppercase">Open Positions</div>
          <div className="text-xl font-bold">{data.open_positions_count}</div>
        </div>
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-center">
          <div className="text-xs text-slate-400 uppercase">Closed Trades</div>
          <div className="text-xl font-bold">{data.closed_trades_count}</div>
        </div>
      </div>

      {/* Open Positions Table */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h3 className="text-sm uppercase tracking-wide text-slate-400 mb-3">Open Positions</h3>
        {positions.length === 0 ? (
          <p className="text-sm text-slate-500">No open positions.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-slate-400 border-b border-slate-700">
                  <th className="text-left py-2">Ticker</th>
                  <th className="text-right">Shares</th>
                  <th className="text-right">Entry</th>
                  <th className="text-right">Last</th>
                  <th className="text-right">P&L</th>
                  <th className="text-right">Return</th>
                  <th className="text-left">Reasoning</th>
                </tr>
              </thead>
              <tbody>
                {positions.map(pos => {
                  const pnl = (pos.last_price - pos.entry_price) * pos.shares
                  const ret = ((pos.last_price - pos.entry_price) / pos.entry_price) * 100
                  return (
                    <tr key={pos.ticker} className="border-b border-slate-700/50">
                      <td className="py-2 font-bold">{pos.ticker}</td>
                      <td className="text-right">{pos.shares}</td>
                      <td className="text-right">${pos.entry_price}</td>
                      <td className="text-right">${pos.last_price}</td>
                      <td className={`text-right ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatMoney(pnl)}
                      </td>
                      <td className={`text-right ${ret >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {ret.toFixed(2)}%
                      </td>
                      <td className="text-xs text-slate-400 max-w-xs truncate">{pos.reasoning}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Trade History */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h3 className="text-sm uppercase tracking-wide text-slate-400 mb-3">Recent Trade History</h3>
        {history.length === 0 ? (
          <p className="text-sm text-slate-500">No trades yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-slate-400 border-b border-slate-700">
                  <th className="text-left py-2">Ticker</th>
                  <th className="text-right">Entry</th>
                  <th className="text-right">Exit</th>
                  <th className="text-right">Shares</th>
                  <th className="text-right">P&L</th>
                  <th className="text-right">Return</th>
                  <th className="text-right">Hold Time</th>
                </tr>
              </thead>
              <tbody>
                {[...history].reverse().map(trade => (
                  <tr key={trade.closed_at + trade.ticker} className="border-b border-slate-700/50">
                    <td className="py-2 font-bold">{trade.ticker}</td>
                    <td className="text-right">${trade.entry_price}</td>
                    <td className="text-right">${trade.exit_price}</td>
                    <td className="text-right">{trade.shares}</td>
                    <td className={`text-right ${trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatMoney(trade.pnl)}
                    </td>
                    <td className={`text-right ${trade.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {trade.return_pct?.toFixed(2)}%
                    </td>
                    <td className="text-right text-xs text-slate-400">
                      {(trade.hold_seconds / 3600).toFixed(1)}h
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default Portfolio
