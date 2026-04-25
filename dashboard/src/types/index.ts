export type AgentStatus = "idle" | "running" | "done" | "error" | "coming_soon"

export interface Agent {
  id: number
  name: string
  role: string
  model: string
  status: AgentStatus
  lastRun: string | null
  lastOutput: string | null
  agentFile: string
}

export interface PendingOutput {
  output_id?: string | null
  filename: string
  agentName: string
  contentType: string
  preview: string
  timestamp: string
  filepath: string
  notion_page_id?: string
  notion_url?: string
}

export interface BrandProfile {
  brand_name: string
  product: string
  price_india: string
  price_international: string
  price_beta: string
  audience: string[]
  platforms: string[]
  bottlenecks: string[]
  phase?: string
  railway_url?: string
  business_type?: string
  industry?: string
  brand_brief?: string
}

export interface NavItem {
  id: string
  label: string
  icon: string
  path: string
}

export interface ActivityItem {
  agent: string
  status: string
  icon: string
  summary: string
  timestamp: string
}

export interface BrandSummary {
  brand_name: string
  product: string
  phase: string
  platforms: string[]
  bottlenecks: string[]
  audience: string[]
  price_india: string
  price_international: string
  railway_url: string
  // Agent-first fields
  instagram_handle: string
  competitor_handles: string[]
  brand_face: string
  tone_specifics: string
  content_goal_90d: string
  what_to_never_say: string
  weekly_post_target: string
  // Metrics
  posts_scripted: number
  agents_run: number
  agents_approved: number
  notion_pending: number
  notion_approved: number
  notion_rejected: number
  completed_agents: string[]
  activity_feed: ActivityItem[]
  keys: {
    anthropic: boolean
    elevenlabs: boolean
    notion: boolean
    fal: boolean
  }
}

export interface NotionCard {
  agent: string
  output_type: string
  notion_url: string
  page_id: string
  timestamp: string
  status: "pending_approval" | "approved" | "rejected"
}

export interface ApiResponse<T> {
  success: boolean
  data: T
  error?: string
}
