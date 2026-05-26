import { cn } from "@/lib/utils";
import type { AgentStatus } from "@/store/appStore";

interface StatusDotProps {
  status: AgentStatus;
  className?: string;
}

export function StatusDot({ status, className }: StatusDotProps) {
  return (
    <span
      className={cn(
        "inline-block h-[6px] w-[6px] rounded-full flex-shrink-0",
        status === "running" && "bg-[var(--status-running)] animate-pulse",
        status === "success" && "bg-[var(--status-success)]",
        status === "error" && "bg-[var(--status-error)]",
        status === "queued" && "bg-[var(--status-queued)]",
        status === "blocked" && "bg-[var(--status-blocked)]",
        status === "idle" && "bg-[var(--status-blocked)]",
        className
      )}
    />
  );
}
