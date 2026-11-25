// src/hooks/useGridData.js
import { useState, useEffect, useCallback } from 'react'

const WS_URL = import.meta.env.VITE_GRID_WS_URL || 'ws://localhost:8000/ws/grid-live'

const EMPTY_INTERSECTION = {
  phase: 0, phase_name: 'Loading...', time_in_phase: 0,
  traffic: { queue: {}, wait: {}, vehicles: {}, total_wait: 0, total_queue: 0 },
}

export function useGridData() {
  const [intersections, setIntersections] = useState({
    A: EMPTY_INTERSECTION, B: EMPTY_INTERSECTION,
    C: EMPTY_INTERSECTION, D: EMPTY_INTERSECTION,
  })
  const [comparison, setComparison] = useState({
    cumulative_adaptive_wait: 0, cumulative_fixed_wait: 0, improvement_pct: 0,
  })
  const [waitHistory, setWaitHistory] = useState([])
  const [decisionLog, setDecisionLog] = useState([])
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    let ws, reconnectTimer
    const connect = () => {
      ws = new WebSocket(WS_URL)
      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        reconnectTimer = setTimeout(connect, 3000)
      }
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        const raw = msg.data || msg
        if (raw.type === 'pong') return
        if (raw.intersections) setIntersections(raw.intersections)
        setComparison({
          cumulative_adaptive_wait: raw.cumulative_adaptive_wait ?? 0,
          cumulative_fixed_wait: raw.cumulative_fixed_wait ?? 0,
          improvement_pct: raw.improvement_pct ?? 0,
        })
        if (raw.wait_history) setWaitHistory(raw.wait_history)
        if (raw.decision_log) setDecisionLog(raw.decision_log)
      }
    }
    connect()
    return () => { clearTimeout(reconnectTimer); ws?.close() }
  }, [])

  return { intersections, comparison, waitHistory, decisionLog, connected }
}