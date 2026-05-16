import { createClient } from './supabase'

// Returns the current access token without triggering Supabase network calls
// when the session is still valid. Falls back to a full getSession() refresh
// only when the in-memory session is missing.
export async function getAccessToken(): Promise<string | null> {
  const supabase = createClient()
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}
