import { Component, useEffect, type ReactNode } from "react"
import { Routes, Route, Navigate, useLocation } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { TooltipProvider } from "@/components/ui/tooltip"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { ClientDashboardPage } from "@/pages/ClientDashboardPage"
import { ReviewPage } from "@/pages/ReviewPage"
import { CalendarPage } from "@/pages/CalendarPage"
import { InsightsPage } from "@/pages/InsightsPage"
import { AuthPage } from "@/pages/AuthPage"
import { OnboardingPage } from "@/pages/OnboardingPage"
import { AdminOverviewPage } from "@/pages/AdminOverviewPage"
import { AdminClientsPage } from "@/pages/AdminClientsPage"
import { AdminRevenuePage } from "@/pages/AdminRevenuePage"
import { AdminSystemPage } from "@/pages/AdminSystemPage"
import { useAppStore } from "@/store/appStore"
import { useAuthStore } from "@/store/authStore"
import { useBrandStore } from "@/store/brandStore"
import { useBrands } from "@/hooks/useGridApi"
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

function AdminGuard({ children }: { children: ReactNode }) {
  const { isSuperAdmin } = useAuthStore()
  if (!isSuperAdmin) return <Navigate to="/" replace />
  return <>{children}</>
}

function OnboardingGuard({ children }: { children: ReactNode }) {
  const location = useLocation()
  const { data } = useBrands()
  const { setBrands, setActiveBrand, brands } = useBrandStore()
  const { isSuperAdmin } = useAuthStore()

  useEffect(() => {
    if (data?.brands && data.brands.length > 0) {
      const mapped = data.brands.map((b) => ({ slug: b.slug, name: b.name, handle: b.handle }))
      setBrands(mapped)
      if (!brands.find((b) => b.slug === mapped[0].slug)) {
        setActiveBrand(mapped[0])
      }
    }
  }, [data, setBrands, setActiveBrand, brands])

  if (isSuperAdmin) return <>{children}</>

  const hasBrands = (data?.brands?.length ?? 0) > 0
  if (!hasBrands && location.pathname !== "/onboarding") {
    return <Navigate to="/onboarding" replace />
  }

  return <>{children}</>
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <AuthGate>
            <ShortcutBindings />
            <OnboardingGuard>
            <DashboardLayout>
              <Routes>
                {/* Client routes — accessible to all */}
                <Route path="/" element={<ClientDashboardPage />} />
                <Route path="/review" element={<ReviewPage />} />
                <Route path="/calendar" element={<CalendarPage />} />
                <Route path="/insights" element={<InsightsPage />} />
                <Route path="/onboarding" element={<OnboardingPage />} />

                {/* Admin routes — super admin only */}
                <Route path="/admin" element={<AdminGuard><AdminOverviewPage /></AdminGuard>} />
                <Route path="/admin/clients" element={<AdminGuard><AdminClientsPage /></AdminGuard>} />
                <Route path="/admin/revenue" element={<AdminGuard><AdminRevenuePage /></AdminGuard>} />
                <Route path="/admin/system" element={<AdminGuard><AdminSystemPage /></AdminGuard>} />

                {/* Catch-all */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </DashboardLayout>
            </OnboardingGuard>
          </AuthGate>
        </TooltipProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}
