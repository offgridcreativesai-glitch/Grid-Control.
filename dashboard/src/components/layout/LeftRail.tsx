import { NavLink, useNavigate } from "react-router-dom";
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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useBrandStore } from "@/store/brandStore";
import { useAuthStore } from "@/store/authStore";
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
  { path: "/memory", icon: BrainCircuit, label: "Memory" },
  { path: "/connections", icon: Plug, label: "Connections" },
];

export function LeftRail() {
  const { activeBrand, brands, setActiveBrand } = useBrandStore();
  const { user, signOut } = useAuthStore();
  const navigate = useNavigate();

  return (
    <TooltipProvider delayDuration={0}>
      <nav className="flex h-full w-16 flex-col items-center border-r border-border bg-background py-3">
        {/* Brand Switcher */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="mb-4 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-card hover:bg-secondary transition-colors">
              <span className="text-xs font-semibold text-primary">
                {activeBrand.name.slice(0, 2).toUpperCase()}
              </span>
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
        <div className="flex flex-1 flex-col items-center gap-1">
          {navItems.map((item) => (
            <Tooltip key={item.path}>
              <TooltipTrigger asChild>
                <NavLink
                  to={item.path}
                  end={item.path === "/"}
                  className={({ isActive }) =>
                    cn(
                      "flex h-10 w-10 items-center justify-center rounded-md transition-colors",
                      isActive
                        ? "bg-secondary text-foreground"
                        : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                    )
                  }
                >
                  <item.icon className="h-5 w-5" />
                </NavLink>
              </TooltipTrigger>
              <TooltipContent side="right">{item.label}</TooltipContent>
            </Tooltip>
          ))}
        </div>

        {/* Sign out + Grid Control Logo */}
        <div className="mt-auto flex flex-col items-center gap-1">
          {user && (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={() => signOut()}
                  className="flex h-10 w-10 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">Sign out ({user.email})</TooltipContent>
            </Tooltip>
          )}
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex h-10 w-10 items-center justify-center">
                <div className="grid grid-cols-2 gap-0.5">
                  <div className="h-1.5 w-1.5 rounded-[1px] bg-primary" />
                  <div className="h-1.5 w-1.5 rounded-[1px] bg-muted-foreground" />
                  <div className="h-1.5 w-1.5 rounded-[1px] bg-muted-foreground" />
                  <div className="h-1.5 w-1.5 rounded-[1px] bg-primary" />
                </div>
              </div>
            </TooltipTrigger>
            <TooltipContent side="right">GRID CONTROL</TooltipContent>
          </Tooltip>
        </div>
      </nav>
    </TooltipProvider>
  );
}
