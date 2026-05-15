import React, { useEffect, useState } from 'react'
import { API_URL } from '../config'

function EmployeeCard({ emp, depth = 0, onSelect, selected, showControls, onFire }) {
  const statusColor =
    emp.performance >= 75 ? 'border-green-500' :
    emp.performance >= 45 ? 'border-yellow-500' :
    'border-red-500'

  const perfBadge =
    emp.performance >= 75 ? 'bg-green-600' :
    emp.performance >= 45 ? 'bg-yellow-600' :
    'bg-red-600'

  return (
    <div className={`ml-${Math.min(depth * 4, 12)} mb-2`} style={{ marginLeft: depth * 24 }}>
      <div
        onClick={() => onSelect(emp)}
        className={`flex items-center gap-3 p-3 bg-slate-800 border ${statusColor} rounded-xl cursor-pointer hover:bg-slate-750 transition ${selected?.id === emp.id ? 'ring-2 ring-violet-500' : ''}`}
      >
        <div className="w-12 h-12 rounded-full overflow-hidden bg-slate-700 flex-shrink-0">
          {emp.pic ? (
            <img
              src={emp.pic}
              alt={emp.name}
              className="w-full h-full object-cover"
              onError={(e) => {
                e.target.parentElement.innerHTML = `<div class="w-full h-full flex items-center justify-center text-lg font-bold text-slate-300">${emp.id.replace('EMP-', '')}</div>`
              }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-lg font-bold text-slate-300">
              {emp.id.replace('EMP-', '')}
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm truncate">{emp.name}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded text-white ${perfBadge}`}>
              {emp.performance?.toFixed?.(0) ?? 0}%
            </span>
          </div>
          <div className="text-xs text-slate-400 truncate">{emp.title}</div>
          <div className="text-xs text-slate-500">{emp.department}</div>
        </div>
        {showControls && emp.performance < 40 && emp.total_tasks >= 10 && (
          <button
            onClick={(e) => { e.stopPropagation(); onFire(emp) }}
            className="px-2 py-1 text-xs bg-red-600 hover:bg-red-500 rounded text-white font-bold"
          >
            FIRE
          </button>
        )}
      </div>
      {emp.children?.map((child) => (
        <EmployeeCard
          key={child.id}
          emp={child}
          depth={depth + 1}
          onSelect={onSelect}
          selected={selected}
          showControls={showControls}
          onFire={onFire}
        />
      ))}
    </div>
  )
}

function OrgChart() {
  const [tree, setTree] = useState([])
  const [terminated, setTerminated] = useState([])
  const [company, setCompany] = useState('SCC')
  const [selected, setSelected] = useState(null)
  const [showTermed, setShowTermed] = useState(false)
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({ total_active: 0, total_ever_hired: 0, total_terminated: 0 })

  useEffect(() => {
    fetch(`${API_URL}/api/org-chart`)
      .then((r) => r.json())
      .then((d) => {
        setTree(d.tree || [])
        setCompany(d.company || 'SCC')
      })
      .catch(() => {})

    fetch(`${API_URL}/api/employees`)
      .then((r) => r.json())
      .then((d) => {
        setStats(d.stats || {})
      })
      .catch(() => {})

    fetch(`${API_URL}/api/employees/terminated`)
      .then((r) => r.json())
      .then((d) => {
        setTerminated(d.terminated || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))

    const iv = setInterval(() => {
      fetch(`${API_URL}/api/org-chart`).then((r) => r.json()).then((d) => setTree(d.tree || [])).catch(() => {})
      fetch(`${API_URL}/api/employees/terminated`).then((r) => r.json()).then((d) => setTerminated(d.terminated || [])).catch(() => {})
    }, 60000)
    return () => clearInterval(iv)
  }, [])

  const handleFire = (emp) => {
    if (!window.confirm(`Fire ${emp.name} (${emp.title})? This cannot be undone.`)) return
    // Frontend placeholder; real fire action handled by backend
    setSelected(null)
  }

  const flattenTree = (nodes) => {
    const out = []
    const walk = (arr) => {
      for (const n of arr) {
        out.push(n)
        if (n.children) walk(n.children)
      }
    }
    walk(nodes)
    return out
  }

  const allEmps = flattenTree(tree)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{company} Organization</h2>
          <p className="text-sm text-slate-400">
            {stats.total_active} active · {stats.total_terminated} terminated · {stats.total_ever_hired} ever hired
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowTermed(!showTermed)}
            className={`px-3 py-1 rounded text-xs font-bold ${showTermed ? 'bg-violet-600 text-white' : 'bg-slate-700 text-slate-300'}`}
          >
            {showTermed ? 'Hide' : 'Show'} Past Employees
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-4 text-xs text-slate-400">
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-green-500" /> ≥75%</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-yellow-500" /> 45-74%</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-red-500" /> &lt;45%</span>
        <span className="ml-auto">Performance from bot_registry accuracy</span>
      </div>

      {/* Org Chart */}
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-5">
        <h3 className="text-sm uppercase tracking-wide text-slate-400 mb-3">Organization Chart</h3>
        {loading ? (
          <div className="text-center py-10 text-slate-400">Loading org chart...</div>
        ) : tree.length === 0 ? (
          <p className="text-sm text-slate-500">No employees on file.</p>
        ) : (
          <div className="space-y-2 overflow-x-auto">
            {tree.map((emp) => (
              <EmployeeCard
                key={emp.id}
                emp={emp}
                depth={0}
                onSelect={setSelected}
                selected={selected}
                showControls={true}
                onFire={handleFire}
              />
            ))}
          </div>
        )}
      </div>

      {/* Employee Detail Panel */}
      {selected && (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <div className="flex items-start gap-4">
            <div className="w-20 h-20 rounded-full overflow-hidden bg-slate-700 flex-shrink-0">
              {selected.pic ? (
                <img
                  src={selected.pic}
                  alt={selected.name}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    e.target.parentElement.innerHTML = `<div class="w-full h-full flex items-center justify-center text-2xl font-bold text-slate-300">${selected.id?.replace('EMP-', '') || '?'}</div>`
                  }}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-2xl font-bold text-slate-300">
                  {selected.id?.replace('EMP-', '') || '?'}
                </div>
              )}
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-bold">{selected.name}</h3>
              <p className="text-sm text-violet-400 font-medium">{selected.title}</p>
              <p className="text-xs text-slate-400">{selected.department} · Employee #{selected.id}</p>
              <div className="mt-2 grid grid-cols-3 gap-2 text-sm">
                <div className="bg-slate-900 rounded p-2">
                  <div className="text-xs text-slate-500">Performance</div>
                  <div className={`font-bold ${selected.performance >= 75 ? 'text-green-400' : selected.performance >= 45 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {selected.performance?.toFixed?.(1) ?? 0}%
                  </div>
                </div>
                <div className="bg-slate-900 rounded p-2">
                  <div className="text-xs text-slate-500">Tasks</div>
                  <div className="font-bold">{selected.total_tasks || 0}</div>
                </div>
                <div className="bg-slate-900 rounded p-2">
                  <div className="text-xs text-slate-500">Salary</div>
                  <div className="font-bold">${(selected.salary || 0).toLocaleString()}</div>
                </div>
              </div>
              {selected.bio && (
                <p className="mt-3 text-xs text-slate-400 italic">{selected.bio}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Past Employees */}
      {showTermed && (
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-5">
          <h3 className="text-sm uppercase tracking-wide text-slate-400 mb-3">Past Employees ({terminated.length})</h3>
          {terminated.length === 0 ? (
            <p className="text-sm text-slate-500">No terminated employees on file.</p>
          ) : (
            <div className="space-y-2">
              {terminated.slice().reverse().map((emp) => (
                <div key={emp.id} className="flex items-center gap-3 p-3 bg-slate-800 border border-red-900/50 rounded-xl opacity-60">
                  <div className="w-10 h-10 rounded-full overflow-hidden bg-slate-700 flex-shrink-0">
                    {emp.profile_pic ? (
                      <img src={emp.profile_pic} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-xs font-bold text-slate-500">{emp.id?.replace('EMP-', '')}</div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold">{emp.name} <span className="text-red-400 text-xs font-normal">({emp.termination_reason})</span></div>
                    <div className="text-xs text-slate-500">{emp.title} · {emp.termination_date?.split('T')[0]}</div>
                  </div>
                  <div className="text-xs text-slate-500">
                    Final perf: {emp.performance_score?.toFixed?.(0) ?? 0}%
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default OrgChart
