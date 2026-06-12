// src/components/Header.jsx

/**
 * Top navigation bar.
 * Shows: title, connection status, AI/Manual mode toggle, live clock.
 */

import { useState, useEffect } from 'react'
import { setControlMode } from '../services/api'

export default function Header({ traffic, connected, onModeChange }) {
  const [time, setTime] = useState(new Date())

  // Live clock
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const handleModeToggle = async () => {
    const newMode = !traffic.ai_mode
    try {
      await setControlMode(newMode)
      onModeChange(newMode)
    } catch (e) {
      console.error('Failed to set mode:', e)
    }
  }

  return (
    <header className="border-b border-elevated px-6 py-3 flex items-center justify-between">

      {/* Left: Logo + Title */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-accent/20 border border-accent/40
                        flex items-center justify-center text-accent text-lg">
          🚦
        </div>
        <div>
          <h1 className="text-white font-semibold text-sm leading-none">
            Smart Traffic Control
          </h1>
          <p className="text-muted text-xs mt-0.5">
            Intersection C — Single Junction
          </p>
        </div>
      </div>

      {/* Center: Status indicators */}
      <div className="flex items-center gap-6">

        {/* Connection status */}
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${
            connected ? 'bg-sgreen animate-pulse' : 'bg-sred'
          }`}/>
          <span className="text-xs text-muted font-mono">
            {connected ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>

        {/* Simulation step */}
        <div className="text-xs text-muted font-mono">
          STEP <span className="text-white">{traffic.step}</span>
        </div>

        {/* Running status */}
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${
            traffic.is_running ? 'bg-accent animate-pulse' : 'bg-muted'
          }`}/>
          <span className="text-xs text-muted font-mono">
            {traffic.is_running ? 'SIMULATING' : 'STOPPED'}
          </span>
        </div>
      </div>

      {/* Right: Mode toggle + clock */}
      <div className="flex items-center gap-4">

        {/* AI / Manual toggle */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted">Manual</span>
          <button
            onClick={handleModeToggle}
            className={`relative w-12 h-6 rounded-full transition-colors duration-300 ${
              traffic.ai_mode ? 'bg-accent' : 'bg-elevated'
            }`}
          >
            <div className={`absolute top-1 w-4 h-4 rounded-full bg-white
                             transition-transform duration-300 ${
              traffic.ai_mode ? 'translate-x-7' : 'translate-x-1'
            }`}/>
          </button>
          <span className={`text-xs font-semibold ${
            traffic.ai_mode ? 'text-accent' : 'text-muted'
          }`}>AI</span>
        </div>

        {/* Clock */}
        <div className="text-xs font-mono text-muted border-l border-elevated pl-4">
          {time.toLocaleTimeString()}
        </div>
      </div>

    </header>
  )
}