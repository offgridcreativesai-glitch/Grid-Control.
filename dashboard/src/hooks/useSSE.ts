import { useEffect, useCallback, useRef } from "react"
import { useAppStore } from "@/store/appStore"
import { isDemo } from "@/lib/demo"
import { supabase } from "@/lib/supabase"
import { sseUrl } from "@/lib/sse"

export interface SSEEvent {
  type: string
  agent?: string
  brand?: string
  status?: string
  timestamp?: string
  [key: string]: unknown
}

export function useSSE() {
  const sourceRef = useRef<EventSource | null>(null)

  const connect = useCallback(async () => {
    if (sourceRef.current || isDemo()) return
    const { data } = await supabase.auth.getSession()
    const url = sseUrl(data.session?.access_token)
    if (!url) {
      // Logged out: retry later instead of hammering a guaranteed 401.
      setTimeout(connect, 15000)
      return
    }
    const es = new EventSource(url)
    sourceRef.current = es

    es.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data)
        if (data.type === "agent_status") {
          useAppStore.getState().addActivity({
            agent: data.agent ?? "unknown",
            status: data.status ?? "unknown",
            brand: data.brand ?? "",
            timestamp: data.timestamp ?? new Date().toISOString(),
          })
        }
      } catch {
        // ignore malformed events
      }
    }

    es.onerror = () => {
      es.close()
      sourceRef.current = null
      setTimeout(connect, 5000)
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      sourceRef.current?.close()
      sourceRef.current = null
    }
  }, [connect])
}
