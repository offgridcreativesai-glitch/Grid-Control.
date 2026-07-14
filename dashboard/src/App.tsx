import { Component, useEffect, type ReactNode } from "react"
import { Routes, Route, Navigate, useLocation } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { TooltipProvider } from "@/components/ui/tooltip"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { CommandCenterPage } from "@/pages/CommandCenterPage"
import { ReviewPage } from "@/pages/ReviewPage"
import { CalendarPage } from "@/pages/CalendarPage"
import { InsightsPage } from "@/pages/InsightsPage"
import { ConnectionsPage } from "@/pages/ConnectionsPage"
import { SettingsPage } from "@/pages/SettingsPage"
import { CrewPage } from "@/pages/CrewPage"
import { MemoryPage } from "@/pages/MemoryPage"
import { CreativeLibraryPage } from "@/pages/CreativeLibraryPage"
import { AuthPage } from "@/pages/AuthPage"
import { OnboardingPage } from "@/pages/OnboardingPage"
import { LandingPage } from "@/landing/LandingPage"
import { useAppStore } from "@/store/appStore"
import { useAuthStore } from "@/store/authStore"
import { useBrandStore } from "@/store/brandStore"
import { useBrands } from "@/hooks/useGridApi"
import { useSSE } from "@/hooks/useSSE"
import { seedDemo } from "@/lib/demo"

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
  // DEV-only demo bypass: set localStorage.gc_demo="1" to preview behind the gate.
  // Gated on import.meta.env.DEV — never active in a production build.
  const demo = import.meta.env.DEV && typeof window !== "undefined" && localStorage.getItem("gc_demo") === "1"
  useEffect(() => {
    if (demo) {
      useAuthStore.setState({
        user: { id: "demo", email: "demo@gridcontrol.app" } as never,
        loading: false, isSuperAdmin: false, viewMode: "client",
      })
      seedDemo()
    } else {
      init()
    }
  }, [init, demo])

  if (loading && !demo) {
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

function OnboardingGuard({ children }: { children: ReactNode }) {
  const location = useLocation()
  const { data, isLoading, isError } = useBrands()
  const { setBrands, setActiveBrand } = useBrandStore()
  const demo = import.meta.env.DEV && typeof window !== "undefined" && localStorage.getItem("gc_demo") === "1"

  useEffect(() => {
    if (data?.brands && data.brands.length > 0) {
      const mapped = data.brands.map((b) => ({ slug: b.slug, name: b.name, handle: b.handle }))
      setBrands(mapped)
      // Set active brand only if none is currently selected
      const current = useBrandStore.getState().activeBrand
      if (!current || !mapped.find((b) => b.slug === current.slug)) {
        setActiveBrand(mapped[0])
      }
    }
  }, [data, setBrands, setActiveBrand])

  // Don't redirect while still loading brands from API
  if (isLoading) return null

  // API unreachable (e.g. the Flask backend isn't running) — do NOT mistake this for
  // "no brands / needs onboarding". Show a clear backend-down state, never bounce to onboarding.
  if (isError && !demo) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 bg-background px-6 text-center">
        <p className="text-[15px] font-semibold text-foreground">Can’t reach Grid Control’s backend</p>
        <p className="max-w-sm text-[13px] text-muted-foreground">
          Your data is safe — the API just isn’t responding. Make sure the backend is running, then retry.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="mt-1 rounded-lg bg-primary px-4 py-1.5 text-[13px] font-semibold text-primary-foreground transition-[filter] hover:brightness-110"
        >
          Retry
        </button>
      </div>
    )
  }

  const hasBrands = (data?.brands?.length ?? 0) > 0
  if (!demo && !hasBrands && location.pathname !== "/onboarding") {
    return <Navigate to="/onboarding" replace />
  }

  return <>{children}</>
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/signin" element={<AuthPage />} />
            <Route path="/landing" element={<LandingPage />} />
            <Route path="/onboarding" element={<AuthGate><OnboardingPage /></AuthGate>} />
            <Route path="/*" element={<GatedApp />} />
          </Routes>
        </TooltipProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

function GatedApp() {
  return (
          <AuthGate>
            <ShortcutBindings />
            <OnboardingGuard>
            <DashboardLayout>
              <Routes>
                {/* Single client view — the command center IS the home */}
                <Route path="/" element={<Navigate to="/command" replace />} />
                <Route path="/command" element={<CommandCenterPage />} />
                <Route path="/team" element={<CrewPage />} />
                <Route path="/review" element={<ReviewPage />} />
                <Route path="/calendar" element={<CalendarPage />} />
                <Route path="/insights" element={<InsightsPage />} />
                <Route path="/creative" element={<CreativeLibraryPage />} />
                <Route path="/memory" element={<MemoryPage />} />
                <Route path="/connections" element={<ConnectionsPage />} />
                <Route path="/settings" element={<SettingsPage />} />

                {/* Catch-all */}
                <Route path="*" element={<Navigate to="/command" replace />} />
              </Routes>
            </DashboardLayout>
            </OnboardingGuard>
          </AuthGate>
  )
}
