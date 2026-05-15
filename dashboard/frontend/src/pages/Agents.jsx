import React, { useEffect, useState } from 'react'
import { API_URL } from '../config'

function AgentCard({ agent, depth = 0, onSelect, selected }) {
  const perfColor =
    agent.performance >= 75 ? 'border-green-500' :
    agent.performance >= 45 ? 'border-yellow-500' :
    'border-red-500'

  const perfBadge =
    agent.performance >= 75 ? 'bg-green-600' :
    agent.performance >= 45 ? 'bg-yellow-600' :
    'bg-red-600'

  const statusClass = agent.active
    ? 'bg-slate-800'
    : 'bg-slate-900 opacity-50 grayscale'

  return (
    <div style={{ marginLeft: depth * 24 }} className="mb-2">
      <div
        onClick={() => onSelect(agent)}
        className={`flex items-center gap-3 p-3 ${statusClass} border ${perfColor} rounded-xl cursor-pointer hover:bg-slate-750 transition ${selected?.id === agent.id ? 'ring-2 ring-violet-500' : ''}`}
      >
        <div className="w-12 h-12 rounded-full overflow-hidden bg-slate-700 flex-shrink-0">
          <img
            src={agent.pic || `/assets/real_faces/${agent.id.toLowerCase()}.jpg`}
            alt={agent.name}
            className="w-full h-full object-cover"
            onError={(e) => {
              e.target.parentElement.innerHTML = `<div class="w-full h-full flex items-center justify-center text-lg font-bold text-slate-300">${agent.id.replace('AGT-', '')}</div>`
            }}
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm truncate">{agent.name}</span>
            {!agent.active && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-red-700 text-white font-bold">TERMINATED</span>
            )}
            {agent.on_pip && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-orange-600 text-white font-bold">ON PIP</span>
            )}
            <span className={`text-xs px-1.5 py-0.5 rounded text-white ${perfBadge}`}>
              {agent.performance?.toFixed?.(0) ?? 0}%
            </span>
          </div>
          <div className="text-xs text-violet-400 font-medium truncate">{agent.title}</div>
          <div className="text-xs text-slate-500">{agent.department}</div>
        </div>
      </div>
      {agent.children?.map((child) => (
        <AgentCard key={child.id} agent={child} depth={depth + 1} onSelect={onSelect} selected={selected} />
      ))}
    </div>
  )
}

function Agents() {
  const [agents, setAgents] = useState([])
  const [tree, setTree] = useState([])
  const [selected, setSelected] = useState(null)
  const [meetings, setMeetings] = useState([])
  const [board, setBoard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filterDept, setFilterDept] = useState('all')

  // Departments from agents list
  const depts = [...new Set(agents.map(a => a.department || 'Unknown'))].sort()

  useEffect(() => {
    fetch(`${API_URL}/api/agents`)
      .then(r => r.json())
      .then(d => { setAgents(d.agents || []); setLoading(false) })
      .catch(() => setLoading(false))

    fetch(`${API_URL}/api/agent-org-chart`)
      .then(r => r.json())
      .then(d => setTree(d.tree || []))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!selected) { setMeetings([]); setBoard(null); return }

    fetch(`${API_URL}/api/agent-meetings/${selected.id}`)
      .then(r => r.json())
      .then(d => setMeetings(d.meetings || []))
      .catch(() => {})

    fetch(`${API_URL}/api/agent-board/${selected.id}`)
      .then(r => r.json())
      .then(d => setBoard(d))
      .catch(() => {})
  }, [selected])

  const filteredAgents = filterDept === 'all'
    ? agents
    : agents.filter(a => a.department === filterDept)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Agent Ecosystem</h2>
          <p className="text-sm text-slate-400">
            {agents.filter(a => a.active).length} active · {agents.filter(a => !a.active).length} terminated · {agents.length} total
          </p>
        </div>
        <div className="flex gap-2">
          <select
            value={filterDept}
            onChange={(e) => setFilterDept(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded px-3 py-1 text-sm text-slate-300"
          >
            <option value="all">All Departments</option>
            {depts.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-4 text-xs text-slate-400">
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-green-500" /> ≥75%</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-yellow-500" /> 45-74%</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-red-500" /> &lt;45%</span>
        <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-orange-600" /> PIP</span>
        <span className="ml-auto">Click agent for board + meetings</span>
      </div>

      {/* Main: Org Chart + Detail Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Org Tree */}
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-5">
          <h3 className="text-sm uppercase tracking-wide text-slate-400 mb-3">Organization</h3>
          {loading ? (
            <div className="text-center py-10 text-slate-400">Loading agents...</div>
          ) : tree.length === 0 ? (
            <p className="text-sm text-slate-500">No agents active.</p>
          ) : (
            <div className="space-y-2 overflow-x-auto">
              {tree.map((agent) => (
                <AgentCard key={agent.id} agent={agent} depth={0} onSelect={setSelected} selected={selected} />
              ))}
            </div>
          )}
        </div>

        {/* Right: Detail Panel */}
        <div className="space-y-4">
          {selected ? (
            <>
              {/* Agent Profile */}
              <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
                <div className="flex items-start gap-4">
                  <div className="w-20 h-20 rounded-full overflow-hidden bg-slate-700 flex-shrink-0">
                    <img
                      src={selected.pic || `/assets/real_faces/${selected.id?.toLowerCase()}.jpg`}
                      alt={selected.name}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.target.parentElement.innerHTML = `<div class="w-full h-full flex items-center justify-center text-2xl font-bold text-slate-300">${selected.id?.replace('AGT-', '') || '?'}</div>`
                      }}
                    />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-bold">{selected.name}</h3>
                    <p className="text-sm text-violet-400 font-medium">{selected.title}</p>
                    <p className="text-xs text-slate-400">{selected.department} · Agent {selected.id}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {selected.on_pip && (
                        <span className="text-xs px-2 py-0.5 rounded bg-orange-600 text-white font-bold">ON PIP — {selected.rework_count}x rework</span>
                      )}
                      {!selected.active && (
                        <span className="text-xs px-2 py-0.5 rounded bg-red-700 text-white font-bold">TERMINATED</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
                  <div className="bg-slate-900 rounded p-2">
                    <div className="text-xs text-slate-500">Accuracy</div>
                    <div className={`font-bold ${selected.performance >= 75 ? 'text-green-400' : selected.performance >= 45 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {selected.performance?.toFixed?.(1) ?? 0}%
                    </div>
                  </div>
                  <div className="bg-slate-900 rounded p-2">
                    <div className="text-xs text-slate-500">Tasks</div>
                    <div className="font-bold">{selected.tasks_completed || 0} / {(selected.tasks_completed||0) + (selected.tasks_failed||0)}</div>
                  </div>
                  <div className="bg-slate-900 rounded p-2">
                    <div className="text-xs text-slate-500">Salary</div>
                    <div className="font-bold">${(selected.salary || 0).toLocaleString()}</div>
                  </div>
                </div>

                {selected.responsibilities && (
                  <div className="mt-3">
                    <div className="text-xs text-slate-500 uppercase mb-1">Responsibilities</div>
                    <ul className="text-xs text-slate-300 space-y-0.5 list-disc list-inside">
                      {selected.responsibilities.map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                  </div>
                )}
              </div>

              {/* Mini Board */}
              {board && (
                <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
                  <h4 className="text-xs uppercase tracking-wide text-slate-400 mb-2">Agent Board</h4>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    {['To Do', 'In Progress', 'Done'].map(sec => (
                      <div key={sec} className="bg-slate-800 rounded p-2">
                        <div className="text-slate-500 uppercase text-[10px]">{sec}</div>
                        <div className="font-bold text-sm">{(board[sec] || []).length}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Meetings */}
              <div className="bg-slate-900 border border-slate-700 rounded-xl p-4">
                <h4 className="text-xs uppercase tracking-wide text-slate-400 mb-2">Agent Meetings ({meetings.length})</h4>
                {meetings.length === 0 ? (
                  <p className="text-xs text-slate-500">No meetings on record.</p>
                ) : (
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {meetings.map((m, i) => (
                      <div key={i} className="bg-slate-800 rounded p-2 text-xs">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-violet-400 font-bold">{m.topic?.slice(0, 50)}</span>
                          <span className="text-slate-500">{m.timestamp?.split('T')[0]}</span>
                        </div>
                        <div className="text-slate-400">{m.summary?.slice(0, 120)}</div>
                        {m.decisions?.length > 0 && (
                          <div className="mt-1 text-slate-500">
                            → {m.decisions[0]}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="bg-slate-900 border border-slate-700 rounded-xl p-10 text-center text-slate-500">
              Click any agent to view their board, meetings, and history
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Agents
