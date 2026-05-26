import type { AgentStatus } from "@/store/appStore";

export interface Agent {
  id: number;
  slug: string;
  name: string;
  role: string;
  status: AgentStatus;
  lastRun: Date | null;
}

// Canonical 18-agent roster — matches CLAUDE.md / agents/ folder slugs.
// Status + lastRun are seed values; live data overrides via useAgentStatus.
export const AGENTS: Agent[] = [
  { id: 0,  slug: "ceo-brain",            name: "CEO Brain",            role: "Orchestrates all agent activities",     status: "idle", lastRun: null },
  { id: 1,  slug: "strategy-agent",       name: "Strategy Agent",       role: "Defines content strategy and goals",    status: "idle", lastRun: null },
  { id: 2,  slug: "content-planner",      name: "Content Planner",      role: "Plans weekly content calendar",         status: "idle", lastRun: null },
  { id: 3,  slug: "script-writer",        name: "Script Writer",        role: "Writes scripts and captions",           status: "idle", lastRun: null },
  { id: 4,  slug: "creative-director",    name: "Creative Director",    role: "Oversees visual direction",             status: "idle", lastRun: null },
  { id: 5,  slug: "ad-strategist",        name: "Ad Strategist",        role: "Plans paid media campaigns",            status: "idle", lastRun: null },
  { id: 6,  slug: "data-analyst",         name: "Data Analyst",         role: "Analyzes performance metrics",          status: "idle", lastRun: null },
  { id: 7,  slug: "funnel-specialist",    name: "Funnel Specialist",    role: "Optimizes conversion funnels",          status: "idle", lastRun: null },
  { id: 8,  slug: "trend-researcher",     name: "Trend Researcher",     role: "Identifies trending topics",            status: "idle", lastRun: null },
  { id: 9,  slug: "website-agent",        name: "Website Agent",        role: "Manages website updates",               status: "idle", lastRun: null },
  { id: 10, slug: "brand-guardian",       name: "Brand Guardian",       role: "Ensures brand consistency",             status: "idle", lastRun: null },
  { id: 11, slug: "seo-aeo-agent",        name: "SEO+AEO Agent",        role: "Optimizes for search and AI",           status: "idle", lastRun: null },
  { id: 12, slug: "email-marketing-agent",name: "Email Marketing Agent",role: "Creates email campaigns",               status: "idle", lastRun: null },
  { id: 13, slug: "community-manager",    name: "Community Manager",    role: "Engages with community",                status: "idle", lastRun: null },
  { id: 14, slug: "dm-customer-hunter",   name: "DM+Customer Hunter",   role: "Handles DMs and outreach",              status: "idle", lastRun: null },
  { id: 15, slug: "carousel-designer",    name: "Carousel Designer",    role: "Creates carousel content",              status: "idle", lastRun: null },
  { id: 16, slug: "trend-sentinel",       name: "Trend Sentinel",       role: "Monitors real-time trends",             status: "idle", lastRun: null },
  { id: 17, slug: "performance-tracker",  name: "Performance Tracker",  role: "Tracks KPIs and reports",               status: "idle", lastRun: null },
];

export function getAgentById(id: number): Agent | undefined {
  return AGENTS.find((agent) => agent.id === id);
}

export function getAgentBySlug(slug: string): Agent | undefined {
  return AGENTS.find((agent) => agent.slug === slug);
}
