import { useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  CheckSquare,
  Bot,
  Calendar,
  BarChart3,
  BrainCircuit,
  Plug,
  SlidersHorizontal,
  FileText,
  Search,
} from "lucide-react";
import { useAppStore } from "@/store/appStore";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";

const navItems = [
  { path: "/command", icon: LayoutDashboard, label: "Command", description: "Dashboard overview" },
  { path: "/team", icon: Bot, label: "Your team", description: "The agent crew" },
  { path: "/review", icon: CheckSquare, label: "Review", description: "Approval queue" },
  { path: "/calendar", icon: Calendar, label: "Calendar", description: "Content calendar" },
  { path: "/insights", icon: BarChart3, label: "Insights", description: "Performance analytics" },
  { path: "/memory", icon: BrainCircuit, label: "Memory", description: "What the team remembers" },
  { path: "/connections", icon: Plug, label: "Connections", description: "Platform accounts" },
  { path: "/settings", icon: SlidersHorizontal, label: "Settings", description: "Publishing & spend" },
];

export function CommandPalette() {
  const navigate = useNavigate();
  const { isCommandOpen, setCommandOpen, setBrainOpen } = useAppStore();

  const handleSelect = (path: string) => {
    navigate(path);
    setCommandOpen(false);
  };

  const handleOpenBrain = () => {
    setBrainOpen(true);
    setCommandOpen(false);
  };

  return (
    <CommandDialog open={isCommandOpen} onOpenChange={setCommandOpen}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        
        <CommandGroup heading="Navigation">
          {navItems.map((item) => (
            <CommandItem
              key={item.path}
              value={item.label}
              onSelect={() => handleSelect(item.path)}
            >
              <item.icon className="mr-2 h-4 w-4 text-muted-foreground" />
              <span>{item.label}</span>
              <span className="ml-auto text-xs text-muted-foreground">
                {item.description}
              </span>
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading="Actions">
          <CommandItem onSelect={handleOpenBrain}>
            <Search className="mr-2 h-4 w-4 text-muted-foreground" />
            <span>Open The Brain</span>
            <span className="ml-auto text-xs text-muted-foreground font-mono">⌘J</span>
          </CommandItem>
          <CommandItem onSelect={() => handleSelect("/review")}>
            <FileText className="mr-2 h-4 w-4 text-muted-foreground" />
            <span>Review pending drafts</span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
