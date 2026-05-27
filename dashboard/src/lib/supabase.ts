import { createClient, type SupabaseClient } from "@supabase/supabase-js"

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || ""
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || ""

function initSupabase(): SupabaseClient {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    console.warn("[GRID CONTROL] Supabase env vars missing — auth disabled. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in dashboard/.env.local")
    return createClient("https://placeholder.supabase.co", "placeholder-key")
  }
  return createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
}

export const supabase = initSupabase()
