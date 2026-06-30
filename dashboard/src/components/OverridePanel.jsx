// src/components/OverridePanel.jsx

/**
 * Manual operator control panel.
 * Allows forcing specific signal phases with a reason.
 */

import { useState } from 'react'
import { overridePhase } from '../services/api'

// India-style: one direction at a time, 4 independent override buttons
const PHASES = [
  { id: 0, name: 'North', color: 'sgreen', desc: 'North ↑ only' },
  { id: 2, name: 'East',  color: 'sgreen', desc: 'East → only'  },
  { id: 4, name: 'South', color: 'sgreen', desc: 'South ↓ only' },
  { id: 6, name: 'West',  color: 'sgreen', desc: 'West ← only'  },
]

export default function OverridePanel({ onOverride }) {
  const [duration, setDuration] = useState(30)
  const [reason,   setReason]   = useState('')
  const [loading,  setLoading]  = useState(false)
  const [message,  setMessage]  = useState(null)

  const handleOverride = async (phase) => {
    setLoading(true)
    setMessage(null)
    try {
      const res = await overridePhase(
        phase,
        duration || null,
        reason || null
      )
      setMessage({ type: 'success', text: res.message })
      if (onOverride) onOverride()
    } catch (e) {
      setMessage({ type: 'error', text: 'Override failed. Check backend.' })
    }
    setLoading(false)
    // Clear message after 3 seconds
    setTimeout(() => setMessage(null), 3000)
  }

  return (
    <div className="bg-panel rounded-xl p-4 border border-elevated">
      <h3 className="text-sm font-semibold text-white mb-3">
        Manual Override
      </h3>

      {/* Duration selector */}
      <div className="mb-3">
        <label className="text-xs text-muted block mb-1">
          Hold duration (seconds)
        </label>
        <div className="flex gap-2">
          {[15, 30, 45, 60].map(d => (
            <button
              key={d}
              onClick={() => setDuration(d)}
              className={`flex-1 py-1.5 rounded text-xs font-mono transition-colors ${
                duration === d
                  ? 'bg-accent text-navy font-semibold'
                  : 'bg-elevated text-muted hover:text-white'
              }`}
            >
              {d}s
            </button>
          ))}
        </div>
      </div>

      {/* Reason input */}
      <div className="mb-3">
        <label className="text-xs text-muted block mb-1">
          Reason (optional)
        </label>
        <input
          type="text"
          value={reason}
          onChange={e => setReason(e.target.value)}
          placeholder="e.g. Emergency vehicle on North"
          className="w-full bg-elevated border border-elevated rounded px-3 py-2
                     text-xs text-white placeholder-muted focus:outline-none
                     focus:border-accent transition-colors"
        />
      </div>

      {/* Phase buttons — one per direction */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        {PHASES.map(p => (
          <button
            key={p.id}
            onClick={() => handleOverride(p.id)}
            disabled={loading}
            className="py-3 rounded-lg border text-xs font-semibold
                       transition-all duration-200 disabled:opacity-50
                       border-sgreen/40 text-sgreen hover:bg-sgreen/10 active:bg-sgreen/20"
          >
            <div className="text-sm mb-0.5">{p.name} Green</div>
            <div className="text-muted font-normal">{p.desc}</div>
          </button>
        ))}
      </div>

      {/* Status message */}
      {message && (
        <div className={`text-xs rounded px-3 py-2 font-mono ${
          message.type === 'success'
            ? 'bg-sgreen/10 text-sgreen border border-sgreen/20'
            : 'bg-sred/10 text-sred border border-sred/20'
        }`}>
          {message.text}
        </div>
      )}
    </div>
  )
}