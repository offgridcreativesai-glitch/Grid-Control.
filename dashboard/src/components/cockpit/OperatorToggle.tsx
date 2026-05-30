/**
 * Operator mode toggle — ported from app.jsx, with the PORT FIX applied.
 *
 * Operator mode does NOT auto-run actions. It unlocks the Brain's edit/run tools for the
 * operator; every output still passes the approval gate. Super-admin only — the hook 403s
 * for everyone else, so the toggle simply doesn't render for non-operators.
 */
import { Lock, LockOpen } from "lucide-react"
import { useAuthStore } from "@/store/authStore"
import { useOperatorMode, useSetOperatorMode } from "@/hooks/useGridApi"

export function OperatorToggle() {
  const { isSuperAdmin } = useAuthStore()
  const { data, isError } = useOperatorMode(isSuperAdmin)
  const setMode = useSetOperatorMode()

  // Not an operator (or endpoint 403'd) → don't show the control at all.
  if (!isSuperAdmin || isError) return null

  const on = !!data?.data?.on
  const pending = setMode.isPending

  return (
    <button
      onClick={() => !pending && setMode.mutate(!on)}
      disabled={pending}
      className="flex items-center gap-2 rounded-lg border border-white/[0.07] bg-white/[0.02] py-1.5 pl-2.5 pr-1.5 transition-colors hover:border-white/[0.12] disabled:opacity-60"
      title={
        on
          ? "Operator mode ON — the Brain can run edit/bash tools. Approvals still required."
          : "Operator mode OFF — the Brain proposes only. Turn on to unlock edit/run tools."
      }
    >
      {on ? (
        <LockOpen size={14} style={{ color: "var(--accent)" }} />
      ) : (
        <Lock size={14} className="text-zinc-500" />
      )}
      <span className="text-[12px] font-medium text-zinc-400">Operator mode</span>
      <span
        className="relative h-[18px] w-[32px] rounded-full transition-colors"
        style={{ background: on ? "var(--accent)" : "rgba(255,255,255,0.1)" }}
      >
        <span
          className="absolute top-[2px] h-[14px] w-[14px] rounded-full bg-white transition-all"
          style={{ left: on ? 16 : 2 }}
        />
      </span>
    </button>
  )
}
