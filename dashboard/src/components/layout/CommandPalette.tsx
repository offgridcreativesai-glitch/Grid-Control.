import { useNavigate } from "react-router-dom";
import {
  Home,
  CheckSquare,
  Bot,
  Calendar,
  BarChart3,
  Settings,
  Play,
  FileText,
  Search,
} from "lucide-react";
import { useAppStore } from "@/store/appStore";
import { AGENTS } from "@/data/agents";
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
  { path: "/", icon: Home, label: "Command", description: "Dashboard overview" },
  { path: "/review", icon: CheckSquare, label: "Review", description: "Approval queue" },
  { path: "/agents", icon: Bot, label: "Agents", description: "Agent control panel" },
  { path: "/calendar", icon: Calendar, label: "Calendar", description: "Content calendar" },
  { path: "/insights", icon: BarChart3, label: "Insights", description: "Performance analytics" },
  { path: "/system", icon: Settings, label: "System", description: "Settings & configuration" },
];

export function CommandPalette() {
  const navigate = useNavigate();
  const { isCommandOpen, setCommandOpen, setBrainOpen } = useAppStore();

  const handleSelect = (path: string) => {
    navigate(path);
    setCommandOpen(false);
  };

  const handleRunAgent = (agentId: number) => {
    // In a real app, this would trigger the agent
    console.log(`Running agent ${agentId}`);
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

        <CommandSeparator />

        <CommandGroup heading="Run Agent">
          {AGENTS.slice(0, 6).map((agent) => (
            <CommandItem
              key={agent.id}
              value={`run ${agent.name}`}
              onSelect={() => handleRunAgent(agent.id)}
            >
              <Play className="mr-2 h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-xs text-muted-foreground mr-2">
                {String(agent.id).padStart(2, "0")}
              </span>
              <span>{agent.name}</span>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
