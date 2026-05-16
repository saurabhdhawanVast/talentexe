import { NextResponse, type NextRequest } from 'next/server'

interface SupabaseSession {
  access_token: string
  refresh_token: string
  user?: { id: string }
}

// Reads the Supabase session from cookies and decodes the JWT locally.
// Makes zero network calls to Supabase — avoids auth rate limit errors.
function getSessionFromCookies(request: NextRequest): SupabaseSession | null {
  const authCookie = request.cookies.getAll().find(
    (c) => c.name.includes('-auth-token') && !c.name.includes('code-verifier')
  )
  if (!authCookie?.value) return null

  try {
    const raw = decodeURIComponent(authCookie.value)

    // Cookie may be a JSON array (chunked) or a plain JSON object
    const parsed = JSON.parse(raw)
    const session: SupabaseSession = Array.isArray(parsed) ? parsed[0] : parsed

    if (!session?.access_token) return null

    // Decode JWT payload to check expiry — no network call needed
    const payloadB64 = session.access_token.split('.')[1]
    const payload = JSON.parse(atob(payloadB64))
    if ((payload.exp as number) * 1000 < Date.now()) return null

    return session
  } catch {
    return null
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const response = NextResponse.next({ request })

  const session = getSessionFromCookies(request)

  // Block /admin/* — admin uses Django Admin only
  if (pathname.startsWith('/admin')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  // Root redirect
  if (pathname === '/') {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  // /set-password requires a session
  if (pathname.startsWith('/set-password')) {
    if (!session) {
      return NextResponse.redirect(new URL('/login', request.url))
    }
    return response
  }

  // Protected routes — require session
  // must_change_password is enforced in each layout (which already calls /auth/me/)
  if (pathname.startsWith('/hr') || pathname.startsWith('/employee')) {
    if (!session) {
      return NextResponse.redirect(new URL('/login', request.url))
    }
  }

  // Already logged in and hitting /login — redirect to appropriate dashboard
  if (pathname === '/login' && session) {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'
      const res = await fetch(`${apiBase}/api/v1/auth/me/`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      })
      if (res.ok) {
        const { data } = await res.json()
        if (data.must_change_password) {
          return NextResponse.redirect(new URL('/set-password', request.url))
        }
        if (data.role === 'hr') {
          return NextResponse.redirect(new URL('/hr/dashboard', request.url))
        }
        if (data.role === 'employee') {
          return NextResponse.redirect(new URL('/employee/profile', request.url))
        }
      }
    } catch {
      // If backend is down, stay on login
    }
  }

  return response
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon\\.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|css|js|woff|woff2|ttf|otf|eot|map)).*)',
  ],
}
