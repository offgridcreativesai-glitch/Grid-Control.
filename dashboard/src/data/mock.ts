import type { Platform, AgentStatus } from "@/store/appStore";

export interface KPI {
  label: string;
  value: number;
  delta: number;
  unit?: string;
}

export interface ActivityEvent {
  id: string;
  agentId: number;
  agentName: string;
  action: string;
  timestamp: Date;
  status: AgentStatus;
}

export interface ScheduledPost {
  id: string;
  platform: Platform;
  caption: string;
  scheduledTime: Date;
  status: AgentStatus;
}

export interface PendingApproval {
  id: string;
  platform: Platform;
  draftedBy: string;
  scheduledTime: Date;
  title?: string;
  caption: string;
  hashtags: string[];
  script?: string;
  imageUrl?: string;
  slideImages?: string[];   // carousel slide PNG paths (relative to project root)
  status: "pending" | "approved" | "rejected";
}

export interface CalendarPost {
  id: string;
  platform: Platform;
  caption: string;
  scheduledTime: Date;
  status: AgentStatus;
}

export interface InsightMetric {
  date: string;
  value: number;
}

export interface TopPost {
  id: string;
  platform: Platform;
  caption: string;
  impressions: number;
  engagements: number;
  saves: number;
  postedAt: Date;
}

// KPIs for Command page
export const COMMAND_KPIS: KPI[] = [
  { label: "Posts shipped 7d", value: 23, delta: 12.5 },
  { label: "Pending approvals", value: 7, delta: -22.2 },
  { label: "Total impressions 7d", value: 847320, delta: 8.3 },
  { label: "New followers 7d", value: 1247, delta: 15.8 },
];

// Activity timeline events
export const ACTIVITY_EVENTS: ActivityEvent[] = [
  { id: "1", agentId: 16, agentName: "Trend Sentinel", action: "Detected viral audio trend on TikTok #productivity", timestamp: new Date(Date.now() - 1000 * 60 * 2), status: "success" },
  { id: "2", agentId: 3, agentName: "Script Writer", action: "Drafted Instagram carousel: \"5 AI tools founders need\"", timestamp: new Date(Date.now() - 1000 * 60 * 8), status: "running" },
  { id: "3", agentId: 13, agentName: "Community Manager", action: "Replied to 12 comments on LinkedIn post", timestamp: new Date(Date.now() - 1000 * 60 * 15), status: "success" },
  { id: "4", agentId: 6, agentName: "Data Analyst", action: "Generated weekly performance report", timestamp: new Date(Date.now() - 1000 * 60 * 22), status: "success" },
  { id: "5", agentId: 0, agentName: "CEO Brain", action: "Coordinated morning content review cycle", timestamp: new Date(Date.now() - 1000 * 60 * 35), status: "success" },
  { id: "6", agentId: 8, agentName: "Trend Researcher", action: "Identified 3 emerging topics in AI/startup space", timestamp: new Date(Date.now() - 1000 * 60 * 48), status: "success" },
  { id: "7", agentId: 11, agentName: "SEO+AEO Agent", action: "Failed to update meta descriptions", timestamp: new Date(Date.now() - 1000 * 60 * 55), status: "error" },
  { id: "8", agentId: 14, agentName: "DM+Customer Hunter", action: "Sent 8 personalized outreach DMs", timestamp: new Date(Date.now() - 1000 * 60 * 62), status: "success" },
  { id: "9", agentId: 2, agentName: "Content Planner", action: "Updated content calendar for next week", timestamp: new Date(Date.now() - 1000 * 60 * 78), status: "success" },
  { id: "10", agentId: 15, agentName: "Carousel Designer", action: "Created visual assets for LinkedIn carousel", timestamp: new Date(Date.now() - 1000 * 60 * 95), status: "queued" },
];

// Scheduled posts for "Up next" section
export const SCHEDULED_POSTS: ScheduledPost[] = [
  { id: "sp1", platform: "x", caption: "Mornings hit different when your stack is dialed in. The 3-tool setup we swear by for deep work →", scheduledTime: new Date(Date.now() + 1000 * 60 * 30), status: "success" },
  { id: "sp2", platform: "instagram", caption: "Stop building features. Start solving problems. Here's how we prioritize at AskGauravAI →", scheduledTime: new Date(Date.now() + 1000 * 60 * 90), status: "queued" },
  { id: "sp3", platform: "linkedin", caption: "I spent $50K on AI tools last year. Here's what actually moved the needle →", scheduledTime: new Date(Date.now() + 1000 * 60 * 180), status: "queued" },
  { id: "sp4", platform: "tiktok", caption: "POV: Your AI agent just outperformed your marketing team", scheduledTime: new Date(Date.now() + 1000 * 60 * 240), status: "queued" },
  { id: "sp5", platform: "youtube", caption: "How I Built a 6-Figure Brand with Zero Employees", scheduledTime: new Date(Date.now() + 1000 * 60 * 360), status: "queued" },
];

// Pending approvals
export const PENDING_APPROVALS: PendingApproval[] = [
  {
    id: "pa1",
    platform: "instagram",
    draftedBy: "Script Writer",
    scheduledTime: new Date(Date.now() + 1000 * 60 * 120),
    caption: "The future isn't about working harder—it's about working with AI.\n\nHere are 5 ways I use Claude daily:\n\n1. Morning brief synthesis\n2. Content ideation sprints\n3. Code review assistance\n4. Research deep dives\n5. Strategic planning sessions\n\nWhich one are you trying first?",
    hashtags: ["#AIFounder", "#Productivity", "#FutureOfWork", "#ClaudeAI", "#StartupLife"],
    status: "pending",
  },
  {
    id: "pa2",
    platform: "x",
    draftedBy: "Trend Sentinel",
    scheduledTime: new Date(Date.now() + 1000 * 60 * 60),
    caption: "Hot take: Most \"AI tools\" are just GPT wrappers with a $50/mo price tag.\n\nThe real edge? Learning to prompt well.\n\nThread on my exact prompting framework 🧵",
    hashtags: [],
    status: "pending",
  },
  {
    id: "pa3",
    platform: "linkedin",
    draftedBy: "Content Planner",
    scheduledTime: new Date(Date.now() + 1000 * 60 * 240),
    caption: "I fired my marketing team.\n\nNot because they weren't good.\n\nBecause 18 AI agents are better.\n\nHere's the controversial truth about building a one-person marketing machine:\n\n[Long-form content follows...]",
    hashtags: ["#AIMarketing", "#SoloFounder", "#ContentStrategy"],
    status: "pending",
  },
  {
    id: "pa4",
    platform: "tiktok",
    draftedBy: "Trend Researcher",
    scheduledTime: new Date(Date.now() + 1000 * 60 * 180),
    caption: "POV: You just automated 80% of your content workflow ✨",
    hashtags: ["#techtok", "#aitools", "#productivity"],
    script: "Open on desk setup shot\n\n\"So I just spent 6 months building this...\"\n\n[Screen recording of GRID CONTROL dashboard]\n\n\"18 AI agents. One command center. Zero burnout.\"\n\n[Show calendar view]\n\n\"It plans my content, writes my scripts, even responds to comments.\"\n\n[Close on approval queue]\n\n\"All I do? Hit approve. Or tweak and approve.\"\n\n[End card]",
    status: "pending",
  },
  {
    id: "pa5",
    platform: "youtube",
    draftedBy: "Script Writer",
    scheduledTime: new Date(Date.now() + 1000 * 60 * 1440),
    caption: "How I Run a Personal Brand Empire with AI Agents",
    hashtags: [],
    script: "INTRO (0:00-0:45)\nHook: \"What if I told you I run a content empire... and I haven't manually written a post in 3 months?\"\n\nPART 1: THE PROBLEM (0:45-3:00)\nContent burnout is real. Traditional social media management doesn't scale.\n\nPART 2: THE SOLUTION (3:00-8:00)\nIntroducing GRID CONTROL and the 18-agent system.\n\n[Continue...]",
    status: "pending",
  },
  {
    id: "pa6",
    platform: "instagram",
    draftedBy: "Carousel Designer",
    scheduledTime: new Date(Date.now() + 1000 * 60 * 300),
    caption: "Your morning routine is killing your productivity.\n\nSwipe to see what I changed →",
    hashtags: ["#MorningRoutine", "#Productivity", "#FounderLife"],
    status: "pending",
  },
  {
    id: "pa7",
    platform: "x",
    draftedBy: "CEO Brain",
    scheduledTime: new Date(Date.now() + 1000 * 60 * 45),
    caption: "Unpopular opinion:\n\nYou don't need a social media manager.\n\nYou need a social media system.\n\nHere's the difference:",
    hashtags: [],
    status: "pending",
  },
];

// Calendar posts (next 30 days)
export function generateCalendarPosts(): CalendarPost[] {
  const posts: CalendarPost[] = [];
  const platforms: Platform[] = ["x", "instagram", "linkedin", "tiktok", "youtube"];
  const captions = [
    "The best founders I know share one thing: they ship daily.",
    "AI won't replace you. Someone using AI will.",
    "Your network is your net worth. Here's how I think about it:",
    "Stop optimizing. Start publishing.",
    "The gap between idea and execution is smaller than ever.",
    "Monday motivation: Build something people want.",
    "Three lessons from scaling to 100K followers:",
    "What I learned from 1000 rejected pitches.",
    "The tools I use to run a one-person business:",
    "Controversial take on personal branding...",
  ];

  const now = new Date();
  for (let day = 0; day < 35; day++) {
    const numPosts = Math.floor(Math.random() * 4) + 1;
    for (let i = 0; i < numPosts; i++) {
      const date = new Date(now);
      date.setDate(date.getDate() + day);
      date.setHours(8 + Math.floor(Math.random() * 12), Math.floor(Math.random() * 60));
      
      posts.push({
        id: `cp-${day}-${i}`,
        platform: platforms[Math.floor(Math.random() * platforms.length)],
        caption: captions[Math.floor(Math.random() * captions.length)],
        scheduledTime: date,
        status: day < 0 ? "success" : day === 0 && date < now ? "success" : "queued",
      });
    }
  }
  return posts;
}

// Insights data
export const INSIGHTS_KPIS: KPI[] = [
  { label: "Impressions", value: 2847320, delta: 12.3 },
  { label: "Engagements", value: 89420, delta: 8.7 },
  { label: "Followers", value: 127845, delta: 4.2 },
  { label: "Save rate", value: 3.2, delta: 0.5, unit: "%" },
];

export function generateChartData(days: number = 30): InsightMetric[] {
  const data: InsightMetric[] = [];
  const now = new Date();
  let baseValue = 100000;
  
  for (let i = days; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    baseValue += Math.floor(Math.random() * 2000) - 500;
    data.push({
      date: date.toISOString().split("T")[0],
      value: baseValue,
    });
  }
  return data;
}

export const TOP_POSTS: TopPost[] = [
  { id: "tp1", platform: "linkedin", caption: "I spent $100K on courses. Here's what actually worked:", impressions: 245000, engagements: 12400, saves: 3200, postedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3) },
  { id: "tp2", platform: "x", caption: "The best founders I know share one trait: impatience with bureaucracy, patience with people.", impressions: 189000, engagements: 8700, saves: 2100, postedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5) },
  { id: "tp3", platform: "instagram", caption: "Your morning routine is killing your creativity. Here's what I changed:", impressions: 156000, engagements: 9200, saves: 4500, postedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7) },
  { id: "tp4", platform: "tiktok", caption: "POV: You just realized your entire business can run on AI", impressions: 342000, engagements: 28000, saves: 8900, postedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2) },
  { id: "tp5", platform: "youtube", caption: "How I Built a $1M Personal Brand in 18 Months", impressions: 89000, engagements: 4200, saves: 1800, postedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 10) },
];

export const WINNING_PATTERNS = [
  "Posts with questions in first line get 2.3x more engagement",
  "LinkedIn carousels outperform text posts by 4x on weekdays",
  "TikTok posts at 7-9am EST see highest completion rates",
  "Threads on X get 3x more impressions than standalone tweets",
];

export const DEAD_PATTERNS = [
  "Posting more than 3x/day on Instagram reduces reach",
  "Generic motivational quotes underperform by 60%",
  "Weekend YouTube uploads see 40% less initial traction",
];

// System settings
export interface Connection {
  id: string;
  name: string;
  type: "platform" | "service";
  connected: boolean;
  lastChecked: Date;
}

export const CONNECTIONS: Connection[] = [
  { id: "x", name: "X (Twitter)", type: "platform", connected: true, lastChecked: new Date(Date.now() - 1000 * 60 * 5) },
  { id: "instagram", name: "Instagram", type: "platform", connected: true, lastChecked: new Date(Date.now() - 1000 * 60 * 5) },
  { id: "linkedin", name: "LinkedIn", type: "platform", connected: true, lastChecked: new Date(Date.now() - 1000 * 60 * 5) },
  { id: "tiktok", name: "TikTok", type: "platform", connected: true, lastChecked: new Date(Date.now() - 1000 * 60 * 5) },
  { id: "youtube", name: "YouTube", type: "platform", connected: false, lastChecked: new Date(Date.now() - 1000 * 60 * 60) },
  { id: "apify", name: "Apify", type: "service", connected: true, lastChecked: new Date(Date.now() - 1000 * 60 * 10) },
  { id: "fal", name: "FAL.ai", type: "service", connected: true, lastChecked: new Date(Date.now() - 1000 * 60 * 15) },
  { id: "notion", name: "Notion", type: "service", connected: true, lastChecked: new Date(Date.now() - 1000 * 60 * 8) },
  { id: "anthropic", name: "Anthropic", type: "service", connected: true, lastChecked: new Date(Date.now() - 1000 * 60 * 2) },
  { id: "supabase", name: "Supabase", type: "service", connected: true, lastChecked: new Date(Date.now() - 1000 * 60 * 12) },
  { id: "meta", name: "Meta Graph API", type: "service", connected: true, lastChecked: new Date(Date.now() - 1000 * 60 * 20) },
  { id: "ga4", name: "Google Analytics 4", type: "service", connected: false, lastChecked: new Date(Date.now() - 1000 * 60 * 120) },
  { id: "gsc", name: "Search Console", type: "service", connected: true, lastChecked: new Date(Date.now() - 1000 * 60 * 30) },
];
