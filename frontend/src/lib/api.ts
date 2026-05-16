const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

export async function apiFetch<T>(
  path: string,
  token: string,
  options: RequestInit = {}
): Promise<T> {
  const isFormData = options.body instanceof FormData

  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    // Don't set Content-Type for FormData — the browser sets it with the multipart boundary
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(options.headers as Record<string, string> | undefined),
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (!res.ok) {
    let message = `API error ${res.status}`
    try {
      const body = await res.json()
      message = body?.error ?? message
    } catch {
      // ignore parse errors
    }
    throw new Error(message)
  }

  return res.json()
}
