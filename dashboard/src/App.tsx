import { Component, useEffect, type ReactNode } from "react"
import { Routes, Route } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { TooltipProvider } from "@/components/ui/tooltip"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { CommandPage } from "@/pages/CommandPage"
import { ReviewPage } from "@/pages/ReviewPage"
import { AgentsPage } from "@/pages/AgentsPage"
import { CalendarPage } from "@/pages/CalendarPage"
import { PublishedPage } from "@/pages/PublishedPage"
import { InsightsPage } from "@/pages/InsightsPage"
import { SystemPage } from "@/pages/SystemPage"
import { AuthPage } from "@/pages/AuthPage"
import { OnboardingPage } from "@/pages/OnboardingPage"
import { BillingPage } from "@/pages/BillingPage"
import { TeamPage } from "@/pages/TeamPage"
import { useAppStore } from "@/store/appStore"
import { useAuthStore } from "@/store/authStore"
import { useSSE } from "@/hooks/useSSE"

class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean; error: Error | null }> {
  constructor(props: { children: ReactNode }) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }
  componentDidCatch(error: Error) {
    console.error("[GRID CONTROL] React error boundary caught:", error)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen items-center justify-center bg-background">
          <div className="max-w-md w-full mx-4 rounded-xl border border-destructive/40 bg-destructive/10 p-8 text-center space-y-4">
            <h2 className="text-foreground font-bold text-lg">Something went wrong</h2>
            <p className="text-destructive text-sm font-mono break-words">
              {this.state.error?.message ?? "An unexpected error occurred"}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mt-2 px-6 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90"
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

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchInterval: 10000, retry: 1 },
  },
})

function ShortcutBindings() {
  const { toggleCommand, toggleBrain } = useAppStore()
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        toggleCommand()
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "j") {
        e.preventDefault()
        toggleBrain()
      }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [toggleCommand, toggleBrain])
  return null
}

function AuthGate({ children }: { children: ReactNode }) {
  const { user, loading, init } = useAuthStore()
  useEffect(() => { init() }, [init])

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-muted-foreground text-sm">Loading...</div>
      </div>
    )
  }

  if (!user) return <AuthPage />
  return <SSEProvider>{children}</SSEProvider>
}

function SSEProvider({ children }: { children: ReactNode }) {
  useSSE()
  return <>{children}</>
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <AuthGate>
            <ShortcutBindings />
            <DashboardLayout>
              <Routes>
                <Route path="/" element={<CommandPage />} />
                <Route path="/review" element={<ReviewPage />} />
                <Route path="/agents" element={<AgentsPage />} />
                <Route path="/agents/:id" element={<AgentsPage />} />
                <Route path="/calendar" element={<CalendarPage />} />
                <Route path="/published" element={<PublishedPage />} />
                <Route path="/insights" element={<InsightsPage />} />
                <Route path="/billing" element={<BillingPage />} />
                <Route path="/team" element={<TeamPage />} />
                <Route path="/system" element={<SystemPage />} />
              <Route path="/onboarding" element={<OnboardingPage />} />
              </Routes>
            </DashboardLayout>
          </AuthGate>
        </TooltipProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}
