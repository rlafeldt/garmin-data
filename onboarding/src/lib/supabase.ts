import { createClient } from "@supabase/supabase-js";

// Fallback values allow the module to load during Next.js build/SSR when
// environment variables are not yet available. Supabase calls will fail at
// runtime if the real values are missing, but the build will succeed.
const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder.supabase.co";
const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder-anon-key";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
