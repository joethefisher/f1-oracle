// Re-export helpers so pages can import from one place.
// Server components: import { createClient } from "@/utils/supabase/server"
// Client components: import { createClient } from "@/utils/supabase/client"
export { createClient as createServerClient } from "@/utils/supabase/server";
export { createClient as createBrowserClient } from "@/utils/supabase/client";
