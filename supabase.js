// Supabase Configuration
// अपनी Supabase Project Details यहां डालें.

const SUPABASE_URL = "YOUR_SUPABASE_URL";
const SUPABASE_PUBLISHABLE_KEY = "YOUR_SUPABASE_PUBLISHABLE_KEY";

// Supabase client
const supabaseClient = supabase.createClient(
  SUPABASE_URL,
  SUPABASE_PUBLISHABLE_KEY
);
