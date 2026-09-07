import {
  NextRequest,
  NextResponse,
} from "next/server";

export function proxy(
  request: NextRequest
) {
  const pathname =
    request.nextUrl.pathname;

  // Öffentlich bleiben:
  // Login/Register-UI, APIs, Next Assets und APK-Download.
  if (
    pathname === "/" ||
    pathname === "/login" ||
    pathname === "/register" ||
    pathname.startsWith("/api/") ||
    pathname.startsWith("/_next/") ||
    pathname.startsWith("/downloads/") ||
    pathname === "/favicon.ico" ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
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

    return NextResponse.redirect(
      loginUrl
    );
  }

  return NextResponse.next();
}

export const config = {
  matcher: "/:path*",
};
