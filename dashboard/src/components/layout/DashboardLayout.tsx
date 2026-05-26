import { type ReactNode } from "react";
import { AnimatePresence } from "framer-motion";
import { LeftRail } from "./LeftRail";
import { TopBar } from "./TopBar";
import { TheBrain } from "./TheBrain";
import { CommandPalette } from "./CommandPalette";
import { useAppStore } from "@/store/appStore";

interface DashboardLayoutProps {
  children: ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { isBrainOpen } = useAppStore();

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* Left Rail - 64px */}
      <LeftRail />

      {/* Main area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Bar - 48px */}
        <TopBar />

        {/* Content area */}
        <div className="flex flex-1 overflow-hidden">
          {/* Main content */}
          <main
            className="flex-1 overflow-auto"
            style={{
              marginRight: isBrainOpen ? "360px" : "0",
              transition: "margin-right 200ms ease-out",
            }}
          >
            {children}
          </main>

          {/* The Brain - Right Rail */}
          <AnimatePresence>
            {isBrainOpen && <TheBrain />}
          </AnimatePresence>
        </div>
      </div>

      {/* Command Palette */}
      <CommandPalette />
    </div>
  );
}
