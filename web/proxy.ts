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

export function proxy(
  request: NextRequest
) {
  const pathname =
    request.nextUrl.pathname;

  const isPublic =
    pathname === "/" ||
    pathname === "/login" ||
    pathname === "/register" ||
    pathname === "/impressum" ||
    pathname === "/datenschutz" ||
    pathname === "/opengraph-image" ||
    pathname.startsWith("/api/") ||
    pathname.startsWith("/_next/") ||
    pathname.startsWith("/downloads/") ||
    pathname === "/favicon.ico" ||
    pathname.includes(".");

  if (isPublic) {
    return secure(
      NextResponse.next()
    );
  }

  const access =
    request.cookies.get(
      "cardyssey_access"
    )?.value;

  const refresh =
    request.cookies.get(
      "cardyssey_refresh"
    )?.value;

  if (!access && !refresh) {
    const loginUrl =
      request.nextUrl.clone();

    loginUrl.pathname = "/login";
    loginUrl.search = "";

    return secure(
      NextResponse.redirect(
        loginUrl
      )
    );
  }

  return secure(
    NextResponse.next()
  );
}

export const config = {
  matcher: "/:path*",
};
