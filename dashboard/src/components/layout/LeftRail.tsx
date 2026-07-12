import { NavLink, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  CheckSquare,
  Calendar,
  BarChart3,
  ChevronDown,
  LogOut,
  LayoutDashboard,
  Plug,
  Bot,
  BrainCircuit,
  SlidersHorizontal,
  ImagePlay,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useBrandStore } from "@/store/brandStore";
import { useAuthStore } from "@/store/authStore";
import { useAppStore } from "@/store/appStore";
import { useWhiteLabel } from "@/hooks/useGridApi";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

// Single client-only navigation. No admin panel, no view toggle.
const navItems = [
  { path: "/command", icon: LayoutDashboard, label: "Home" },
  { path: "/team", icon: Bot, label: "Your team" },
  { path: "/review", icon: CheckSquare, label: "Review" },
  { path: "/calendar", icon: Calendar, label: "Calendar" },
  { path: "/insights", icon: BarChart3, label: "Insights" },
  { path: "/creative", icon: ImagePlay, label: "Creative" },
  { path: "/memory", icon: BrainCircuit, label: "Memory" },
  { path: "/connections", icon: Plug, label: "Connections" },
  { path: "/settings", icon: SlidersHorizontal, label: "Settings" },
];

export function LeftRail() {
  const { isMobileNavOpen, setMobileNavOpen } = useAppStore();

  return (
    <>
      {/* Desktop rail — icon column, hidden below sm */}
      <RailContent variant="rail" className="hidden sm:flex" />

      {/* Mobile drawer — full nav with labels, toggled from TopBar's menu button */}
      <AnimatePresence>
        {isMobileNavOpen && (
          <>
            <motion.div
              key="backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/60 sm:hidden"
              onClick={() => setMobileNavOpen(false)}
            />
            <motion.div
              key="drawer"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "tween", duration: 0.2 }}
              className="fixed inset-y-0 left-0 z-50 sm:hidden"
            >
              <RailContent variant="drawer" className="flex" onNavigate={() => setMobileNavOpen(false)} />
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

function RailContent({
  variant,
  className,
  onNavigate,
}: {
  variant: "rail" | "drawer";
  className?: string;
  onNavigate?: () => void;
}) {
  const { activeBrand, brands, setActiveBrand } = useBrandStore();
  const { user, signOut } = useAuthStore();
  const { data: wl } = useWhiteLabel();
  const navigate = useNavigate();
  const isDrawer = variant === "drawer";
  const platformName = wl?.brand_name || "GRID CONTROL";

  return (
    <TooltipProvider delayDuration={0}>
      <nav
        className={cn(
          "h-full flex-col border-r border-border bg-background py-3",
          isDrawer ? "w-64 items-stretch px-3" : "w-16 items-center",
          className,
        )}
      >
        {/* Brand Switcher */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className={cn(
                "mb-4 flex h-10 items-center rounded-md border border-border bg-card hover:bg-secondary transition-colors",
                isDrawer ? "w-full justify-start gap-2 px-3" : "w-10 justify-center",
              )}
            >
              <span className="text-xs font-semibold text-primary">
                {activeBrand.name.slice(0, 2).toUpperCase()}
              </span>
              {isDrawer && <span className="text-sm font-medium text-foreground">{activeBrand.name}</span>}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent side="right" align="start" className="w-56">
            <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
              Switch brand
            </div>
            {brands.map((brand) => (
              <DropdownMenuItem
                key={brand.slug}
                onClick={() => setActiveBrand(brand)}
                className="flex items-center gap-2"
              >
                {brand.slug === activeBrand.slug && (
                  <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                )}
                <span className={cn(brand.slug !== activeBrand.slug && "ml-3.5")}>
                  {brand.name}
                </span>
                {brand.primary && (
                  <span className="ml-auto text-[10px] text-muted-foreground">primary</span>
                )}
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-muted-foreground" onClick={() => navigate("/onboarding")}>
              <ChevronDown className="mr-2 h-3 w-3 rotate-[-90deg]" />
              New brand
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Navigation */}
        <div className={cn("flex flex-1 flex-col gap-1", isDrawer ? "items-stretch" : "items-center")}>
          {navItems.map((item) => {
            const link = (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === "/"}
                onClick={onNavigate}
                className={({ isActive }) =>
                  cn(
                    "flex items-center rounded-md transition-colors",
                    isDrawer ? "h-11 gap-3 px-3" : "h-10 w-10 justify-center",
                    isActive
                      ? "bg-secondary text-foreground"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                  )
                }
              >
                <item.icon className="h-5 w-5 shrink-0" />
                {isDrawer && <span className="text-sm">{item.label}</span>}
              </NavLink>
            );
            if (isDrawer) return link;
            return (
              <Tooltip key={item.path}>
                <TooltipTrigger asChild>{link}</TooltipTrigger>
                <TooltipContent side="right">{item.label}</TooltipContent>
              </Tooltip>
            );
          })}
        </div>

        {/* Sign out + Grid Control Logo */}
        <div className={cn("mt-auto flex flex-col gap-1", isDrawer ? "items-stretch" : "items-center")}>
          {user && (
            (() => {
              const signOutBtn = (
                <button
                  onClick={() => signOut()}
                  className={cn(
                    "flex items-center rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors",
                    isDrawer ? "h-11 gap-3 px-3" : "h-10 w-10 justify-center",
                  )}
                >
                  <LogOut className="h-4 w-4 shrink-0" />
                  {isDrawer && <span className="text-sm">Sign out ({user.email})</span>}
                </button>
              );
              if (isDrawer) return signOutBtn;
              return (
                <Tooltip>
                  <TooltipTrigger asChild>{signOutBtn}</TooltipTrigger>
                  <TooltipContent side="right">Sign out ({user.email})</TooltipContent>
                </Tooltip>
              );
            })()
          )}
          {!isDrawer && (
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex h-10 w-10 items-center justify-center">
                  {wl?.logo_url ? (
                    <img src={wl.logo_url} alt={platformName} className="h-6 w-6 rounded object-contain" />
                  ) : (
                    <div className="grid grid-cols-2 gap-0.5">
                      <div className="h-1.5 w-1.5 rounded-[1px] bg-primary" style={wl?.accent ? { background: wl.accent } : undefined} />
                      <div className="h-1.5 w-1.5 rounded-[1px] bg-muted-foreground" />
                      <div className="h-1.5 w-1.5 rounded-[1px] bg-muted-foreground" />
                      <div className="h-1.5 w-1.5 rounded-[1px] bg-primary" style={wl?.accent ? { background: wl.accent } : undefined} />
                    </div>
                  )}
                </div>
              </TooltipTrigger>
              <TooltipContent side="right">{platformName}</TooltipContent>
            </Tooltip>
          )}
        </div>
      </nav>
    </TooltipProvider>
  );
}
