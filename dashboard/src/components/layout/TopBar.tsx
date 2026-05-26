import { Search, Bell, MessageSquare } from "lucide-react";
import { useAppStore } from "@/store/appStore";
import { useBrandStore } from "@/store/brandStore";
import { cn } from "@/lib/utils";

export function TopBar() {
  const { toggleCommand, toggleBrain, isBrainOpen } = useAppStore();
  const { activeBrand } = useBrandStore();

  return (
    <header className="flex h-12 items-center justify-between border-b border-border bg-background px-4">
      {/* Left: Brand pill */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1">
          <span className="h-1.5 w-1.5 rounded-full bg-primary" />
          <span className="text-sm font-medium">{activeBrand.name}</span>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {/* Command Palette Trigger */}
        <button
          onClick={toggleCommand}
          className="flex h-8 items-center gap-2 rounded-md border border-border bg-card px-3 text-sm text-muted-foreground hover:bg-secondary transition-colors"
        >
          <Search className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Search</span>
          <kbd className="hidden sm:inline-flex h-5 items-center gap-0.5 rounded border border-border bg-background px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
            <span className="text-xs">⌘</span>K
          </kbd>
        </button>

        {/* Notifications */}
        <button className="relative flex h-8 w-8 items-center justify-center rounded-md hover:bg-secondary transition-colors">
          <Bell className="h-4 w-4 text-muted-foreground" />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-primary" />
        </button>

        {/* Brain Toggle */}
        <button
          onClick={toggleBrain}
          className={cn(
            "flex h-8 items-center gap-2 rounded-md px-3 transition-colors",
            isBrainOpen
              ? "bg-primary text-primary-foreground"
              : "hover:bg-secondary text-muted-foreground"
          )}
        >
          <MessageSquare className="h-4 w-4" />
          <kbd className="hidden sm:inline-flex h-5 items-center gap-0.5 rounded border border-border/50 px-1.5 font-mono text-[10px] font-medium opacity-70">
            <span className="text-xs">⌘</span>J
          </kbd>
        </button>

        {/* Avatar */}
        <button className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary">
          <span className="text-xs font-medium">G</span>
        </button>
      </div>
    </header>
  );
}
