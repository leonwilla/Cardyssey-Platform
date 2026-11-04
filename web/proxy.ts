function renewal(request: NextRequest) {
  if (!request.cookies.get("cardyssey_refresh")?.value) return secure(NextResponse.redirect("https://cardyssey.de/login"));
  const dest = new URL("https://cardyssey.de/api/auth/renew");
  const shop = request.headers.get("host")?.split(":")[0]?.toLowerCase() === "shop.cardyssey.de";
  dest.searchParams.set("returnTo", "https://" + (shop ? "shop.cardyssey.de" : "cardyssey.de") + request.nextUrl.pathname + request.nextUrl.search);
  return secure(NextResponse.redirect(dest));
}
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

const SHOP_PREVIEW_COOKIE = "cardyssey_shop_preview";
const SHOP_PREVIEW_TTL = 7 * 24 * 60 * 60;
async function previewSignature(expiry: number): Promise<string | null> {
  const secret = process.env.CARDYSSEY_SHOP_PREVIEW_SECRET;
  if (!secret || secret.length < 40) return null;
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), {name:"HMAC",hash:"SHA-256"}, false, ["sign"]);
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(`cardyssey-shop-preview:${expiry}`));
  return Array.from(new Uint8Array(signature)).map(byte=>byte.toString(16).padStart(2,"0")).join("");
}
async function validPreview(value: string | undefined): Promise<boolean> {
  if (!value || !/^[0-9]{10,13}\.[0-9a-f]{64}$/.test(value)) return false;
  const [raw, sign] = value.split(".");
  const expiry = Number(raw);
  if (!Number.isSafeInteger(expiry) || expiry <= Math.floor(Date.now()/1000) || expiry > Math.floor(Date.now()/1000)+SHOP_PREVIEW_TTL) return false;
  const expected = await previewSignature(expiry);
  if (!expected) return false;
  let different = 0;
  for (let i=0;i<expected.length;i++) different |= expected.charCodeAt(i)^sign.charCodeAt(i);
  return different===0;
}
async function grantPreview(response: NextResponse): Promise<NextResponse> {
  const expiry = Math.floor(Date.now()/1000)+SHOP_PREVIEW_TTL;
  const signature = await previewSignature(expiry);
  if (signature) response.cookies.set(SHOP_PREVIEW_COOKIE,`${expiry}.${signature}`,{
    path:"/",httpOnly:true,secure:true,sameSite:"lax",maxAge:SHOP_PREVIEW_TTL
  });
  return secure(response);
}

export async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const isStoreHost = request.headers.get("host")?.split(":")[0]?.toLowerCase() === "shop.cardyssey.de";
  if (isStoreHost) {
    const asset = pathname.startsWith("/_next/") || pathname === "/cardyssey-emblem-gold.png" || pathname === "/favicon.ico";
    if (asset) return secure(NextResponse.next());
    if (pathname === "/shop-logout") return secure(NextResponse.redirect(new URL("/",request.url)));
    if (pathname === "/login") return secure(NextResponse.redirect("https://cardyssey.de/login"));
    if (pathname === "/datenschutz" || pathname === "/impressum" || (pathname === "/api/auth/logout" && request.method === "POST")) return secure(NextResponse.next());
    const storefront = pathname === "/" || pathname === "/business-shop";
    const publishedReads = (pathname === "/api/sets" || pathname.startsWith("/api/sets/") || pathname === "/api/shop/offers" || pathname === "/api/shop/catalog-sets") && request.method === "GET";
    const personalReads = (pathname === "/api/shop/wishlist-matches" || pathname === "/api/auth/me" || pathname === "/api/wishlist" || pathname.startsWith("/api/wishlist/")) && (request.method === "GET" || (pathname.startsWith("/api/wishlist/") && request.method === "DELETE") || (pathname === "/api/wishlist" && request.method === "POST"));
    if (!storefront && !publishedReads && !personalReads) return secure(new NextResponse("Not Found",{status:404}));
    const preview = await validPreview(request.cookies.get(SHOP_PREVIEW_COOKIE)?.value);
    const access = request.cookies.get("cardyssey_access")?.value;
    if (access) {
      try {
        const endpoint = (process.env.CARDYSSEY_API_URL || "http://127.0.0.1:8081").replace(/\/$/, "") + "/api/v1/me";
        const response = await fetch(endpoint,{headers:{Authorization:"Bearer "+access},cache:"no-store"});
        if (response.ok) {
          const user = await response.json() as {id?:string};
          const allowed = (process.env.CARDYSSEY_PRIVATE_USER_IDS || "").split(",").map(x=>x.trim());
          if (user.id && allowed.includes(user.id)) {
            const result = pathname === "/" ? NextResponse.rewrite(new URL("/business-shop",request.url)) : NextResponse.next();
            return await grantPreview(result);
          }
        }
      } catch {if (!preview) return secure(new NextResponse("Authentication temporarily unavailable",{status:503}));}
    }
    // Signed browsing permits former approved testers to log out, while the
    // shop remains inaccessible to arbitrary unauthenticated visitors.
    if (preview) {
      if (personalReads) return secure(NextResponse.next());
      return secure(pathname === "/"?NextResponse.rewrite(new URL("/business-shop",request.url)):NextResponse.next());
    }
    return renewal(request);
  }
  // Assets and the authentication entry point remain reachable so approved users can sign in.
  if (pathname === "/login" || pathname === "/register" || pathname === "/impressum" || pathname === "/datenschutz" ||
      pathname === "/api/auth/login" || pathname === "/api/auth/logout" || pathname === "/api/auth/me" || pathname === "/api/auth/renew" ||
      pathname === "/api/internal/private-access" || pathname.startsWith("/_next/") ||
      pathname === "/favicon.ico" || pathname === "/cardyssey-emblem-gold.png" ||
      pathname.startsWith("/images/") || pathname.startsWith("/landing/") ||
      pathname.startsWith("/vendor/") || pathname.startsWith("/app-screenshots/")) {
    return secure(NextResponse.next());
  }
  // Native clients send a bearer token, not browser cookies.
  // Both handlers perform their own backend user and allowlist checks.
  if (pathname === "/api/android/release" || pathname === "/api/private/apk") {
    return secure(NextResponse.next());
  }
  if (pathname === "/api/auth/register") {
    return secure(NextResponse.redirect(new URL("/login",request.url)));
  }
  const token = request.cookies.get("cardyssey_access")?.value;
  if (!token) return renewal(request);
  try {
    const endpoint = (process.env.CARDYSSEY_API_URL || "http://127.0.0.1:8081").replace(/\/$/, "") + "/api/v1/me";
    const verification = await fetch(endpoint, {headers:{Authorization:`Bearer ${token}`},cache:"no-store"});
    if (verification.status === 401) return renewal(request);
    if (verification.ok) {
      const user = await verification.json() as {id?:string};
      const ids = (process.env.CARDYSSEY_PRIVATE_USER_IDS || "").split(",").map(x=>x.trim());
      if (user.id && ids.includes(user.id)) return secure(NextResponse.next());
    }
  } catch { /* fail closed */ }
  return secure(NextResponse.redirect(new URL("/login",request.url)));
}

export const config = {matcher:"/:path*"};
