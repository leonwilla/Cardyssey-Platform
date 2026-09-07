import { cookies } from "next/headers";

const ACCESS_COOKIE = "cardyssey_access";
const REFRESH_COOKIE = "cardyssey_refresh";

export type BackendUser = {
  id: string;
  email: string;
  displayName?: string | null;
  friendCode?: string;
};

type AuthPayload = {
  accessToken: string;
  accessTokenExpiresInSeconds: number;
  refreshToken: string;
  refreshTokenExpiresInSeconds: number;
  user: BackendUser;
};

/*
 * Verhindert parallele Refresh-Requests mit demselben
 * Refresh-Token.
 *
 * Das Ergebnis bleibt kurz im Speicher, damit auch Requests,
 * die wenige Millisekunden später noch mit dem alten Cookie
 * eintreffen, dasselbe rotierte Token-Paar bekommen.
 */
const refreshFlights =
  new Map<
    string,
    Promise<AuthPayload | null>
  >();

function apiBase() {
  return (
    process.env.CARDYSSEY_API_URL ||
    "http://127.0.0.1:8081"
  ).replace(/\/$/, "");
}

export function backendFetch(
  path: string,
  init?: RequestInit
) {
  return fetch(
    `${apiBase()}${path}`,
    {
      cache: "no-store",
      ...init,
    }
  );
}

export async function setAuthCookies(
  payload: AuthPayload
) {
  const jar = await cookies();

  const secure =
    process.env.NODE_ENV ===
    "production";

  jar.set(
    ACCESS_COOKIE,
    payload.accessToken,
    {
      httpOnly: true,
      sameSite: "lax",
      secure,
      path: "/",
      maxAge:
        payload.accessTokenExpiresInSeconds,
    }
  );

  jar.set(
    REFRESH_COOKIE,
    payload.refreshToken,
    {
      httpOnly: true,
      sameSite: "lax",
      secure,
      path: "/",
      maxAge:
        payload.refreshTokenExpiresInSeconds,
    }
  );
}

export async function clearAuthCookies() {
  const jar = await cookies();

  jar.set(
    ACCESS_COOKIE,
    "",
    {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    }
  );

  jar.set(
    REFRESH_COOKIE,
    "",
    {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    }
  );
}

async function performRefresh(
  refreshToken: string
): Promise<AuthPayload | null> {
  try {
    const response =
      await backendFetch(
        "/api/v1/auth/refresh",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            refreshToken,
          }),
        }
      );

    if (!response.ok) {
      return null;
    }

    return (
      await response.json()
    ) as AuthPayload;

  } catch {
    return null;
  }
}

async function refreshSession():
  Promise<AuthPayload | null> {

  const jar = await cookies();

  const refreshToken =
    jar.get(
      REFRESH_COOKIE
    )?.value;

  if (!refreshToken) {
    return null;
  }

  let flight =
    refreshFlights.get(
      refreshToken
    );

  if (!flight) {
    flight =
      performRefresh(
        refreshToken
      );

    refreshFlights.set(
      refreshToken,
      flight
    );

    /*
     * Nicht sofort entfernen:
     * weitere bereits laufende Requests können
     * noch den alten Refresh-Cookie besitzen.
     */
    void flight.then(() => {
      setTimeout(
        () => {
          if (
            refreshFlights.get(
              refreshToken
            ) === flight
          ) {
            refreshFlights.delete(
              refreshToken
            );
          }
        },
        30_000
      );
    });
  }

  const payload =
    await flight;

  if (!payload) {
    await clearAuthCookies();
    return null;
  }

  /*
   * Jeder wartende Route-Handler setzt die neuen
   * Cookies in seiner eigenen Response.
   */
  await setAuthCookies(
    payload
  );

  return payload;
}

export async function authenticatedBackendFetch(
  path: string,
  init?: RequestInit
) {
  const jar = await cookies();

  let accessToken =
    jar.get(
      ACCESS_COOKIE
    )?.value;

  /*
   * Access-Token im Browser bereits abgelaufen:
   * Session per Refresh wiederherstellen.
   */
  if (!accessToken) {
    const refreshed =
      await refreshSession();

    if (!refreshed) {
      return new Response(
        null,
        {
          status: 401,
        }
      );
    }

    accessToken =
      refreshed.accessToken;
  }

  const firstHeaders =
    new Headers(
      init?.headers
    );

  firstHeaders.set(
    "Authorization",
    `Bearer ${accessToken}`
  );

  let response =
    await backendFetch(
      path,
      {
        ...init,
        headers:
          firstHeaders,
      }
    );

  if (
    response.status !== 401
  ) {
    return response;
  }

  /*
   * Access-Token serverseitig abgelaufen:
   * genau einen Refresh durchführen.
   */
  const refreshed =
    await refreshSession();

  if (!refreshed) {
    return response;
  }

  const retryHeaders =
    new Headers(
      init?.headers
    );

  retryHeaders.set(
    "Authorization",
    `Bearer ${refreshed.accessToken}`
  );

  response =
    await backendFetch(
      path,
      {
        ...init,
        headers:
          retryHeaders,
      }
    );

  return response;
}

export async function readBackendJson(
  response: Response
) {
  const text =
    await response.text();

  if (!text) {
    return {};
  }

  try {
    return JSON.parse(text);
  } catch {
    return {
      error:
        "invalid_backend_response",
    };
  }
}
