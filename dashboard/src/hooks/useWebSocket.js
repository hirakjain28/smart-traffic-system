// src/hooks/useWebSocket.js

/**
 * Custom hook for WebSocket connection to backend.
 * 
 * WHAT IS A CUSTOM HOOK?
 * A custom hook is a function that starts with "use" and
 * can use other React hooks inside it.
 * It lets you reuse stateful logic across components.
 * 
 * This hook:
 * - Opens a WebSocket connection to ws://localhost:8000/ws/live
 * - Receives live updates from the simulation
 * - Calls onMessage() whenever new data arrives
 * - Reconnects automatically if connection drops
 * - Sends "ping" every 30 seconds to keep connection alive
 */

import { useEffect, useRef, useCallback } from 'react'

const WS_URL = 'ws://localhost:8000/ws/live'
const RECONNECT_DELAY = 3000   // 3 seconds before reconnecting
const PING_INTERVAL   = 30000  // 30 seconds between pings

export function useWebSocket(onMessage) {
  const wsRef           = useRef(null)   // holds the WebSocket instance
  const reconnectTimer  = useRef(null)   // timer for reconnection
  const pingTimer       = useRef(null)   // timer for keepalive pings
  const mountedRef      = useRef(true)   // track if component is still mounted

  const connect = useCallback(() => {
    // Don't connect if component is unmounted
    if (!mountedRef.current) return

    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('🟢 WebSocket connected')
        // Start keepalive pings
        pingTimer.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, PING_INTERVAL)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          // Ignore pong responses
          if (data.type !== 'pong' && onMessage) {
            onMessage(data)
          }
        } catch (e) {
          // Ignore parse errors
        }
      }

      ws.onclose = () => {
        console.log('🔴 WebSocket disconnected. Reconnecting...')
        clearInterval(pingTimer.current)
        // Reconnect after delay
        if (mountedRef.current) {
          reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY)
        }
      }

      ws.onerror = () => {
        ws.close()
      }

    } catch (e) {
      // Retry on connection failure
      if (mountedRef.current) {
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY)
      }
    }
  }, [onMessage])

  useEffect(() => {
    mountedRef.current = true
    connect()

    // Cleanup on unmount
    return () => {
      mountedRef.current = false
      clearTimeout(reconnectTimer.current)
      clearInterval(pingTimer.current)
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connect])
}