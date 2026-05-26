/**
 * The Brain — chat history persistence per brand and (optionally) per agent.
 *
 * Tier 1 fix: chat history survives page refresh.
 * Tier 1 fix: per-agent scoped chat (each agent slug gets its own thread).
 *
 * Threads are keyed by `${brandSlug}::${scope}` where scope is either
 * "global" (the right-rail Brain) or an agent slug like "script-writer".
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface BrainProposal {
  kind: "edit" | "bash";
  payload: any;
  status: "pending" | "approved" | "rejected" | "executed" | "failed";
  result?: string;
}

export interface BrainMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  proposals?: BrainProposal[];
  createdAt: number;
}

export type BrainScope = "global" | string; // "global" or agent slug

interface BrainStore {
  threads: Record<string, BrainMessage[]>; // key = `${brandSlug}::${scope}`
  scope: BrainScope; // current active scope
  setScope: (scope: BrainScope) => void;
  getThread: (brandSlug: string, scope: BrainScope) => BrainMessage[];
  setThread: (brandSlug: string, scope: BrainScope, msgs: BrainMessage[]) => void;
  appendMessage: (brandSlug: string, scope: BrainScope, msg: BrainMessage) => void;
  updateMessage: (
    brandSlug: string,
    scope: BrainScope,
    msgId: string,
    patch: Partial<BrainMessage>,
  ) => void;
  clearThread: (brandSlug: string, scope: BrainScope) => void;
}

const k = (brand: string, scope: BrainScope) => `${brand}::${scope}`;

export const useBrainStore = create<BrainStore>()(
  persist(
    (set, get) => ({
      threads: {},
      scope: "global",
      setScope: (scope) => set({ scope }),
      getThread: (brand, scope) => get().threads[k(brand, scope)] ?? [],
      setThread: (brand, scope, msgs) =>
        set((s) => ({ threads: { ...s.threads, [k(brand, scope)]: msgs } })),
      appendMessage: (brand, scope, msg) =>
        set((s) => {
          const key = k(brand, scope);
          const cur = s.threads[key] ?? [];
          return { threads: { ...s.threads, [key]: [...cur, msg] } };
        }),
      updateMessage: (brand, scope, msgId, patch) =>
        set((s) => {
          const key = k(brand, scope);
          const cur = s.threads[key] ?? [];
          return {
            threads: {
              ...s.threads,
              [key]: cur.map((m) => (m.id === msgId ? { ...m, ...patch } : m)),
            },
          };
        }),
      clearThread: (brand, scope) =>
        set((s) => {
          const key = k(brand, scope);
          const next = { ...s.threads };
          delete next[key];
          return { threads: next };
        }),
    }),
    {
      name: "grid-control-brain",
      version: 1,
      partialize: (state) => ({ threads: state.threads }),
    },
  ),
);
