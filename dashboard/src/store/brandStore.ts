import { create } from "zustand"
import { persist } from "zustand/middleware"

export interface Brand {
  slug: string
  name: string
  handle?: string
  primary?: boolean
}

// No hardcoded brand seed — the real brand list comes from /api/brands.
// activeBrand starts as an empty sentinel (slug "") so brand-scoped queries stay
// disabled (they guard on activeBrand.slug) until a real brand is onboarded/selected.
const NO_BRAND: Brand = { slug: "", name: "No brand", handle: "" }
const defaultBrands: Brand[] = []

interface Message {
  role: "user" | "agent"
  content: string
  timestamp: string
  agentName?: string
}

interface GroupEntry {
  role: "user" | "group"
  content: string
  timestamp: string
  responses?: { agent: string; message: string; timestamp: string }[]
}

interface BrandStore {
  activeBrand: Brand
  brands: Brand[]
  activeScreen: number
  // Conversation persistence — survives navigation AND page refresh
  individualHistories: Record<string, Record<string, Message[]>>  // brandSlug → agentSlug → messages
  groupHistories: Record<string, GroupEntry[]>                    // brandSlug → group entries
  setActiveBrand: (brand: Brand) => void
  setBrands: (brands: Brand[]) => void
  navigate: (screen: number) => void
  setIndividualHistory: (brandSlug: string, agentSlug: string, messages: Message[]) => void
  appendIndividualMessage: (brandSlug: string, agentSlug: string, msg: Message) => void
  clearIndividualHistory: (brandSlug: string, agentSlug: string) => void
  appendGroupEntry: (brandSlug: string, entry: GroupEntry) => void
  clearGroupHistory: (brandSlug: string) => void
}

export const useBrandStore = create<BrandStore>()(
  persist(
    (set) => ({
      activeBrand: NO_BRAND,
      brands: defaultBrands,
      activeScreen: 1,
      individualHistories: {},
      groupHistories: {},

      setActiveBrand: (brand) => set({ activeBrand: brand }),
      setBrands: (brands) => set({ brands }),
      navigate: (screen) => set({ activeScreen: screen }),

      setIndividualHistory: (brandSlug, agentSlug, messages) =>
        set(state => ({
          individualHistories: {
            ...state.individualHistories,
            [brandSlug]: {
              ...(state.individualHistories[brandSlug] ?? {}),
              [agentSlug]: messages,
            },
          },
        })),

      appendIndividualMessage: (brandSlug, agentSlug, msg) =>
        set(state => {
          const existing = state.individualHistories[brandSlug]?.[agentSlug] ?? []
          return {
            individualHistories: {
              ...state.individualHistories,
              [brandSlug]: {
                ...(state.individualHistories[brandSlug] ?? {}),
                [agentSlug]: [...existing, msg],
              },
            },
          }
        }),

      clearIndividualHistory: (brandSlug, agentSlug) =>
        set(state => {
          const brandHistories = { ...(state.individualHistories[brandSlug] ?? {}) }
          delete brandHistories[agentSlug]
          return {
            individualHistories: {
              ...state.individualHistories,
              [brandSlug]: brandHistories,
            },
          }
        }),

      appendGroupEntry: (brandSlug, entry) =>
        set(state => ({
          groupHistories: {
            ...state.groupHistories,
            [brandSlug]: [...(state.groupHistories[brandSlug] ?? []), entry],
          },
        })),

      clearGroupHistory: (brandSlug) =>
        set(state => ({
          groupHistories: { ...state.groupHistories, [brandSlug]: [] },
        })),
    }),
    {
      name: "grid-control-store",
      version: 3,
      // Only persist what matters across refresh — brands list is always re-fetched from server
      partialize: (state) => ({
        individualHistories: state.individualHistories,
        groupHistories:      state.groupHistories,
        activeBrand:         state.activeBrand,
        activeScreen:        state.activeScreen,
      }),
    }
  )
)
