import { create } from "zustand";

export type Platform = "x" | "instagram" | "linkedin" | "tiktok" | "youtube";
export type AgentStatus = "idle" | "running" | "error" | "success" | "queued" | "blocked";

export interface ActivityEvent {
  agent: string;
  status: string;
  brand: string;
  timestamp: string;
}

export interface AppState {
  // Brain (Claude chat)
  isBrainOpen: boolean;
  toggleBrain: () => void;
  setBrainOpen: (open: boolean) => void;

  // Command palette
  isCommandOpen: boolean;
  toggleCommand: () => void;
  setCommandOpen: (open: boolean) => void;

  // Mobile nav drawer (LeftRail collapses into this below the sm breakpoint)
  isMobileNavOpen: boolean;
  toggleMobileNav: () => void;
  setMobileNavOpen: (open: boolean) => void;

  // Platform filters
  selectedPlatforms: Platform[];
  togglePlatform: (platform: Platform) => void;
  setSelectedPlatforms: (platforms: Platform[]) => void;

  // Live activity feed (SSE)
  activity: ActivityEvent[];
  addActivity: (event: ActivityEvent) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Brain
  isBrainOpen: false,
  toggleBrain: () => set((state) => ({ isBrainOpen: !state.isBrainOpen })),
  setBrainOpen: (open) => set({ isBrainOpen: open }),

  // Command
  isCommandOpen: false,
  toggleCommand: () => set((state) => ({ isCommandOpen: !state.isCommandOpen })),
  setCommandOpen: (open) => set({ isCommandOpen: open }),

  // Mobile nav drawer
  isMobileNavOpen: false,
  toggleMobileNav: () => set((state) => ({ isMobileNavOpen: !state.isMobileNavOpen })),
  setMobileNavOpen: (open) => set({ isMobileNavOpen: open }),

  // Platforms
  selectedPlatforms: ["x", "instagram", "linkedin", "tiktok", "youtube"],
  togglePlatform: (platform) =>
    set((state) => ({
      selectedPlatforms: state.selectedPlatforms.includes(platform)
        ? state.selectedPlatforms.filter((p) => p !== platform)
        : [...state.selectedPlatforms, platform],
    })),
  setSelectedPlatforms: (platforms) => set({ selectedPlatforms: platforms }),

  // Activity
  activity: [],
  addActivity: (event) =>
    set((state) => ({
      activity: [event, ...state.activity].slice(0, 50),
    })),
}));
