import { cn } from "@/lib/utils"
import { BrandSwitcher } from "@/components/BrandSwitcher"

interface NavItem {
  id:     string
  label:  string
  icon:   React.ReactNode
  screen: number
}

const Icons = {
  command: (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor">
      <rect x="1" y="1" width="6" height="6" rx="1.5"/>
      <rect x="9" y="1" width="6" height="6" rx="1.5"/>
      <rect x="1" y="9" width="6" height="6" rx="1.5"/>
      <rect x="9" y="9" width="6" height="6" rx="1.5"/>
    </svg>
  ),
  review: (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor">
      <path d="M12 2H4a2 2 0 00-2 2v10l3-3h7a2 2 0 002-2V4a2 2 0 00-2-2z"/>
    </svg>
  ),
  agents: (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor">
      <circle cx="8" cy="5" r="3"/>
      <path d="M2 14c0-3.3 2.7-6 6-6s6 2.7 6 6"/>
    </svg>
  ),
  brand: (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="2" y="7" width="12" height="8" rx="1"/>
      <path d="M5 7V5a3 3 0 016 0v2"/>
    </svg>
  ),
  system: (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="8" r="2.5"/>
      <path d="M8 1.5v1.8M8 12.7v1.8M1.5 8h1.8M12.7 8h1.8M3.4 3.4l1.3 1.3M11.3 11.3l1.3 1.3M3.4 12.6l1.3-1.3M11.3 4.7l1.3-1.3"/>
    </svg>
  ),
  insights: (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M2 13l4-6 3 4 5-7"/>
      <circle cx="2" cy="13" r="1" fill="currentColor"/>
      <circle cx="6" cy="7" r="1" fill="currentColor"/>
      <circle cx="9" cy="11" r="1" fill="currentColor"/>
      <circle cx="14" cy="4" r="1" fill="currentColor"/>
    </svg>
  ),
}

const NAV_ITEMS: NavItem[] = [
  { id: "command",  label: "Command",  icon: Icons.command,  screen: 1 },
  { id: "review",   label: "Review",   icon: Icons.review,   screen: 2 },
  { id: "agents",   label: "Agents",   icon: Icons.agents,   screen: 3 },
  { id: "brand",    label: "Brand",    icon: Icons.brand,    screen: 4 },
  { id: "system",   label: "System",   icon: Icons.system,   screen: 5 },
  { id: "insights", label: "Insights", icon: Icons.insights, screen: 6 },
]

interface SidebarProps {
  activeScreen: number
  onNavigate:  (screen: number) => void
}

export function Sidebar({ activeScreen, onNavigate }: SidebarProps) {
  return (
    <aside
      style={{ width: 210, flexShrink: 0 }}
      className="flex flex-col h-screen bg-[hsl(var(--gc-sidebar))] border-r border-[hsl(var(--border))]"
    >
      {/* Logo */}
      <div className="px-5 pt-7 pb-6 border-b border-[hsl(var(--border))]">
        <div style={{ fontSize: 13, fontWeight: 800, letterSpacing: 3.5, textTransform: "uppercase" }}
          className="text-[hsl(var(--gc-gold))]">
          Grid Control
        </div>
        <div style={{ fontSize: 10, letterSpacing: "1.5px", textTransform: "uppercase", marginTop: 4 }}
          className="text-[hsl(var(--gc-text-2))]">
          OffGrid Marketing OS
        </div>
      </div>

      {/* Brand Switcher */}
      <BrandSwitcher />

      {/* Nav — 5 items only */}
      <nav className="flex-1 py-4 space-y-0.5 px-3">
        {NAV_ITEMS.map((item) => {
          const isActive = activeScreen === item.screen
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.screen)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all",
                isActive
                  ? "bg-[rgba(201,168,76,0.10)] text-white"
                  : "text-[hsl(var(--gc-text-2))] hover:text-white hover:bg-[hsl(var(--gc-surface2))]"
              )}
              style={{ fontSize: 14, fontWeight: isActive ? 600 : 500 }}
            >
              <span className={cn("shrink-0 transition-colors", isActive ? "text-[hsl(var(--gc-gold))]" : "text-[hsl(var(--gc-text-2))]")}>
                {item.icon}
              </span>
              <span className="truncate">{item.label}</span>
              {isActive && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-[hsl(var(--gc-gold))] shrink-0" />
              )}
            </button>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 pt-4 pb-5 border-t border-[hsl(var(--border))]">
        <div className="flex items-center gap-3">
          <div
            className="flex items-center justify-center rounded-lg bg-[rgba(201,168,76,0.12)] border border-[rgba(201,168,76,0.3)] text-[hsl(var(--gc-gold))] shrink-0"
            style={{ width: 32, height: 32, fontSize: 12, fontWeight: 700 }}>
            GK
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600 }} className="text-white">Gaurav Khanna</div>
            <div style={{ fontSize: 12 }} className="text-[hsl(var(--gc-text-2))]">CEO · OffGrid</div>
          </div>
        </div>
      </div>
    </aside>
  )
}
