import { Component, type ReactNode } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Sidebar } from "@/components/Sidebar"
import { CommandSpace } from "@/spaces/CommandSpace"
import { ReviewSpace }  from "@/spaces/ReviewSpace"
import { AgentsSpace }  from "@/spaces/AgentsSpace"
import { BrandSpace }   from "@/spaces/BrandSpace"
import { SystemSpace }  from "@/spaces/SystemSpace"
import { useBrandStore } from "@/store/brandStore"

// ── Phase 5 Step 1 — Error Boundary ───────────────────────────────────────────

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  constructor(props: { children: ReactNode }) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error) {
    console.error("[GRID CONTROL] React error boundary caught:", error)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen items-center justify-center bg-[hsl(var(--background))]">
          <div className="max-w-md w-full mx-4 rounded-xl border border-red-800 bg-red-950/30 p-8 text-center space-y-4">
            <div className="w-14 h-14 rounded-full bg-red-950 border border-red-800 flex items-center justify-center mx-auto">
              <span className="text-2xl">⚠</span>
            </div>
            <h2 className="text-white font-bold text-lg">Something went wrong</h2>
            <p className="text-red-300 text-sm font-mono break-words">
              {this.state.error?.message ?? "An unexpected error occurred"}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mt-2 px-6 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-sm font-medium hover:opacity-90 transition-opacity"
            >
              Reload
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

// ── App ───────────────────────────────────────────────────────────────────────

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchInterval: 10000,
      retry: 1,
    },
  },
})

const SCREENS: Record<number, ReactNode> = {
  1: <CommandSpace />,
  2: <ReviewSpace  />,
  3: <AgentsSpace  />,
  4: <BrandSpace   />,
  5: <SystemSpace  />,
}

function AppLayout() {
  const { activeScreen, navigate } = useBrandStore()

  return (
    <div className="flex h-screen overflow-hidden bg-[hsl(var(--background))]">
      <Sidebar activeScreen={activeScreen} onNavigate={navigate} />
      <main className="flex-1 overflow-hidden flex flex-col">
        {SCREENS[activeScreen] ?? <CommandSpace />}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <AppLayout />
        </TooltipProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}
