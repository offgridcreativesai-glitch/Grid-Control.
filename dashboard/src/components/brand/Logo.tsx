import { cn } from "@/lib/utils"

/** The Grid Control hex mark. Inherits color via currentColor. */
export function GridMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M16 2.5 27.7 9v14L16 29.5 4.3 23V9L16 2.5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M11 12.5 16 9.7l5 2.8v6L16 21.5l-5-2.8" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <circle cx="16" cy="15.6" r="1.6" fill="currentColor" />
    </svg>
  )
}

export function Wordmark({ small, className }: { small?: boolean; className?: string }) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <GridMark className={cn("text-foreground", small ? "h-6 w-6" : "h-7 w-7")} />
      <span className={cn("font-display font-semibold tracking-[0.18em] text-foreground", small ? "text-sm" : "text-base")}>
        GRID CONTROL
      </span>
    </div>
  )
}
