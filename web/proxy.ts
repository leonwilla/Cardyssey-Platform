import {
  NextRequest,
  NextResponse,
} from "next/server";

function secure(
  response: NextResponse
) {
  response.headers.set(
    "X-Content-Type-Options",
    "nosniff"
  );
  response.headers.set(
    "Strict-Transport-Security",
    "max-age=63072000; includeSubDomains"
  );
  response.headers.set(
    "Referrer-Policy",
    "strict-origin-when-cross-origin"
  );
  response.headers.set(
    "X-Frame-Options",
    "DENY"
  );
  response.headers.set(
    "Permissions-Policy",
    "camera=(self), microphone=(), geolocation=()"
  );
  response.headers.set(
    "Cross-Origin-Opener-Policy",
    "same-origin"
  );
  response.headers.set(
    "Cross-Origin-Resource-Policy",
    "same-site"
  );
  response.headers.set(
    "Content-Security-Policy",
    [
      "default-src 'self'",
      "base-uri 'self'",
      "frame-ancestors 'none'",
      "form-action 'self'",
      "object-src 'none'",
      "img-src 'self' data: blob: https:",
      "media-src 'self' blob:",
      "worker-src 'self' blob:",
      "font-src 'self' data:",
      "style-src 'self' 'unsafe-inline'",
      process.env.NODE_ENV === "development"
        ? "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' 'unsafe-eval'"
        : "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'",
      "connect-src 'self' https:",
      "upgrade-insecure-requests",
    ].join("; ")
  );

  return response;
}

export async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  // Assets and the authentication entry point remain reachable so approved users can sign in.
  if (pathname === "/login" || pathname === "/impressum" || pathname === "/datenschutz" ||
      pathname === "/api/auth/login" || pathname === "/api/auth/logout" ||
      pathname === "/api/internal/private-access" || pathname.startsWith("/_next/") ||
      pathname === "/favicon.ico" || pathname === "/cardyssey-emblem-gold.png" ||
      pathname.startsWith("/images/") || pathname.startsWith("/landing/") ||
      pathname.startsWith("/vendor/") || pathname.startsWith("/app-screenshots/")) {
    return secure(NextResponse.next());
  }
  if (pathname === "/register" || pathname === "/api/auth/register") {
    return secure(NextResponse.redirect(new URL("/login",request.url)));
  }
  const hasSession = request.cookies.has("cardyssey_access") || request.cookies.has("cardyssey_refresh");
  if (!hasSession) return secure(NextResponse.redirect(new URL("/login",request.url)));
  try {
    const verification = await fetch(new URL("/api/internal/private-access",request.url), {
      headers:{cookie: request.headers.get("cookie") ?? ""},cache:"no-store",
    });
    if (verification.status === 204) return secure(NextResponse.next());
  } catch { /* fail closed */ }
  return secure(NextResponse.redirect(new URL("/login?error=access_restricted",request.url)));
}

export const config = {matcher:"/:path*"};
