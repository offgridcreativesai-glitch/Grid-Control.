import { useState, useEffect } from "react"
import { useNavigate, useLocation } from "react-router-dom"
import { motion, AnimatePresence } from "framer-motion"
import { Mail, ArrowRight, Lock, User, CheckCircle2, AlertCircle, Loader2 } from "lucide-react"

/* Google "G" mark */
function GoogleMark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden>
      <path fill="#EA4335" d="M12 10.2v3.9h5.5c-.24 1.4-1.7 4.1-5.5 4.1-3.3 0-6-2.7-6-6.1s2.7-6.1 6-6.1c1.9 0 3.2.8 3.9 1.5l2.7-2.6C16.9 3.3 14.7 2.3 12 2.3 6.9 2.3 2.8 6.4 2.8 11.5S6.9 20.7 12 20.7c5.3 0 8.8-3.7 8.8-9 0-.6-.06-1-.15-1.5H12z" />
    </svg>
  )
}
import { AgentCharacter } from "@/components/AgentCharacter"
import { SpaceBackground } from "@/components/SpaceBackground"
import { GridMark } from "@/components/brand/Logo"
import { useAuthStore } from "@/store/authStore"
import { enterDemo, DEMO_EMAIL } from "@/lib/demo"

/* Glowing network globe that sits behind the card. */
function GlowGlobe() {
  return (
    <div className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[680px] w-[680px] -translate-x-1/2 -translate-y-1/2">
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background:
            "radial-gradient(circle at 50% 45%, rgba(46,107,255,0.24), rgba(120,70,255,0.12) 46%, transparent 68%)",
        }}
      />
      <svg viewBox="0 0 200 200" className="absolute inset-0 h-full w-full animate-[spin_70s_linear_infinite] opacity-30">
        <defs>
          <linearGradient id="globe" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#2E6BFF" />
            <stop offset="1" stopColor="#8a5bff" />
          </linearGradient>
        </defs>
        <g fill="none" stroke="url(#globe)" strokeWidth="0.4">
          <circle cx="100" cy="100" r="80" />
          <ellipse cx="100" cy="100" rx="27" ry="80" />
          <ellipse cx="100" cy="100" rx="54" ry="80" />
          <ellipse cx="100" cy="100" rx="80" ry="27" />
          <ellipse cx="100" cy="100" rx="80" ry="54" />
        </g>
      </svg>
    </div>
  )
}

export function AuthPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { signIn, sendMagicLink, signInWithGoogle, signUp } = useAuthStore()
  const [signup, setSignup] = useState(false)
  const [mode, setMode] = useState<"magic" | "password">("magic")
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  // Landing's "Sign up" button deep-links here with ?mode=signup
  useEffect(() => {
    if (new URLSearchParams(location.search).get("mode") === "signup") setSignup(true)
  }, [location.search])

  function maybeDemo(): boolean {
    if (import.meta.env.DEV && email.trim().toLowerCase() === DEMO_EMAIL) {
      enterDemo()
      navigate("/command")
      return true
    }
    return false
  }

  async function onMagic(e: React.FormEvent) {
    e.preventDefault()
    if (!email.trim() || busy) return
    if (maybeDemo()) return
    setBusy(true)
    setErr(null)
    const { error } = await sendMagicLink(email.trim())
    setBusy(false)
    if (error) setErr(error)
    else setSent(true)
  }

  async function onPassword(e: React.FormEvent) {
    e.preventDefault()
    if (maybeDemo()) return
    if (!email.trim() || !password || busy) return
    setBusy(true)
    setErr(null)
    const { error } = await signIn(email.trim(), password)
    setBusy(false)
    if (error) setErr(error)
    else navigate("/command") // success → onAuthStateChange sets the session
  }

  async function onSignup(e: React.FormEvent) {
    e.preventDefault()
    if (maybeDemo()) return
    if (!email.trim() || !password || busy) return
    setBusy(true)
    setErr(null)
    const { error } = await signUp(email.trim(), password, name.trim())
    setBusy(false)
    if (error) setErr(error)
    else navigate("/onboarding") // new account → set up the first brand
  }

  async function onGoogle() {
    if (busy) return
    setBusy(true)
    setErr(null)
    const { error } = await signInWithGoogle()
    if (error) {
      setErr(error)
      setBusy(false)
      return
    }
    // success → Supabase redirects the whole page to Google. If that
    // redirect doesn't actually happen (blocked, misconfigured), don't
    // leave every button on the page stuck showing a spinner forever.
    setTimeout(() => setBusy(false), 8000)
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-6 py-10">
      <SpaceBackground />

      {/* Atlas — the greeter, anchored bottom-left */}
      <div className="pointer-events-none absolute bottom-0 left-0 hidden h-full w-[46%] items-end lg:flex">
        <div className="origin-bottom-left scale-[1.45] pb-[3vh] pl-[3vw]">
          <AgentCharacter agent="atlas" size="xl" showGlow still />
        </div>
      </div>

      {/* Card */}
      <div className="relative w-full max-w-md lg:ml-[18%]">
        <GlowGlobe />
        <div className="glass-panel relative rounded-3xl px-8 py-9 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.7)]">
          {/* logo lockup */}
          <div className="flex flex-col items-center text-center">
            <GridMark className="h-9 w-9 text-foreground" />
            <p className="mt-3 font-display text-2xl font-semibold tracking-[0.2em] text-foreground">GRID CONTROL</p>
            <p className="mt-1 text-[11px] font-medium tracking-[0.42em] text-primary">TAKE CONTROL.</p>
          </div>

          {/* divider */}
          <div className="my-7 flex items-center gap-3">
            <span className="h-px flex-1 bg-gradient-to-r from-transparent to-border" />
            <span className="h-1 w-1 rounded-full bg-primary shadow-[0_0_8px_2px_rgba(255,77,0,0.7)]" />
            <span className="h-px flex-1 bg-gradient-to-l from-transparent to-border" />
          </div>

          <AnimatePresence mode="wait">
            {sent ? (
              <motion.div
                key="sent"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center py-4 text-center"
              >
                <CheckCircle2 className="h-10 w-10 text-emerald" />
                <p className="mt-4 font-display text-xl font-semibold text-foreground">Check your inbox</p>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  We sent a magic link to <span className="text-foreground">{email}</span>. Click it to enter your command center.
                </p>
                <button
                  onClick={() => setSent(false)}
                  className="mt-6 text-[13px] font-semibold text-foreground/80 transition-colors hover:text-primary"
                >
                  ← Use a different email
                </button>
              </motion.div>
            ) : (
              <motion.div key="form" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <div className="mb-6 text-center">
                  <p className="text-xs font-medium tracking-[0.34em] text-muted-foreground">
                    {signup ? "CREATE YOUR ACCOUNT" : "WELCOME BACK"}
                  </p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {signup ? "Spin up your command center." : "Access your command center."}
                  </p>
                </div>

                {/* Google — works for both sign in and sign up */}
                <button
                  type="button"
                  onClick={onGoogle}
                  disabled={busy}
                  className="mb-4 inline-flex w-full items-center justify-center gap-2.5 rounded-xl border border-input bg-white/[0.04] py-3 text-[14px] font-semibold text-foreground transition-colors hover:bg-white/[0.08] disabled:opacity-50"
                >
                  <GoogleMark className="h-4 w-4" />
                  Continue with Google
                </button>

                <div className="mb-4 flex items-center gap-3">
                  <span className="h-px flex-1 bg-border" />
                  <span className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">or</span>
                  <span className="h-px flex-1 bg-border" />
                </div>

                <form onSubmit={signup ? onSignup : mode === "magic" ? onMagic : onPassword} className="space-y-4">
                  {signup && (
                    <div>
                      <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                        Your name
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          placeholder="Jane Founder"
                          autoComplete="name"
                          className="w-full rounded-xl border border-input bg-black/30 px-4 py-3.5 pr-11 text-[15px] text-foreground outline-none transition-colors placeholder:text-muted-foreground/70 focus:border-primary/60"
                        />
                        <User className="absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      </div>
                    </div>
                  )}
                  <div>
                    <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                      Email address
                    </label>
                    <div className="relative">
                      <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@company.com"
                        autoComplete="email"
                        className="w-full rounded-xl border border-input bg-black/30 px-4 py-3.5 pr-11 text-[15px] text-foreground outline-none transition-colors placeholder:text-muted-foreground/70 focus:border-primary/60"
                      />
                      <Mail className="absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    </div>
                  </div>

                  <AnimatePresence>
                    {(signup || mode === "password") && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden"
                      >
                        <label className="mb-1.5 block text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                          Password
                        </label>
                        <div className="relative">
                          <input
                            type="password"
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            autoComplete="current-password"
                            className="w-full rounded-xl border border-input bg-black/30 px-4 py-3.5 pr-11 text-[15px] text-foreground outline-none transition-colors placeholder:text-muted-foreground/70 focus:border-primary/60"
                          />
                          <Lock className="absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {err && (
                    <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-[12.5px] text-destructive">
                      <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                      {err}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={busy || !email.trim() || ((signup || mode === "password") && !password)}
                    className="group inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-3.5 text-[15px] font-semibold text-primary-foreground shadow-[0_0_36px_-6px_rgba(255,77,0,0.7)] transition-transform hover:scale-[1.01] disabled:opacity-50 disabled:hover:scale-100"
                  >
                    {busy ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        {signup ? "Creating…" : mode === "magic" ? "Sending…" : "Signing in…"}
                      </>
                    ) : (
                      <>
                        {signup ? "Create account" : mode === "magic" ? "Send Magic Link" : "Sign In"}
                        <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                      </>
                    )}
                  </button>
                </form>

                {/* divider */}
                <div className="my-6 flex items-center gap-3">
                  <span className="h-px flex-1 bg-gradient-to-r from-transparent to-border" />
                  <span className="h-1 w-1 rounded-full bg-border" />
                  <span className="h-px flex-1 bg-gradient-to-l from-transparent to-border" />
                </div>

                {!signup && (
                  <p className="text-center text-sm text-muted-foreground">
                    {mode === "magic" ? "Or sign in with " : "Or use a "}
                    <button
                      type="button"
                      onClick={() => setMode(mode === "magic" ? "password" : "magic")}
                      className="font-semibold text-primary transition-opacity hover:opacity-80"
                    >
                      {mode === "magic" ? "password" : "magic link"}
                    </button>
                  </p>
                )}

                <p className="mt-3 text-center text-sm text-muted-foreground">
                  {signup ? "Already have an account? " : "New to Grid Control? "}
                  <button
                    type="button"
                    onClick={() => { setSignup(!signup); setErr(null) }}
                    className="font-semibold text-primary transition-opacity hover:opacity-80"
                  >
                    {signup ? "Log in" : "Create an account"}
                  </button>
                </p>

                {import.meta.env.DEV && (
                  <button
                    type="button"
                    onClick={() => { enterDemo(); navigate("/command") }}
                    className="mt-5 w-full rounded-xl border border-emerald/30 bg-emerald/[0.06] py-2.5 text-[13px] font-semibold text-emerald transition-colors hover:bg-emerald/[0.12]"
                  >
                    Explore the live demo →
                  </button>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
