import {
  backendFetch,
  readBackendJson,
  setAuthCookies,
} from "@/lib/server/cardyssey-api";

export async function POST(
  request: Request
) {
  const contentType =
    request.headers.get(
      "content-type"
    ) ?? "";

  const formMode =
    contentType.includes(
      "application/x-www-form-urlencoded"
    ) ||
    contentType.includes(
      "multipart/form-data"
    );

  let body: string;
  let shopReturnTo = "";

  if (formMode) {
    const form =
      await request.formData();
    try {
      const requested=new URL(String(form.get("returnTo")||""));
      if(requested.protocol==="https:" && requested.hostname==="shop.cardyssey.de" && !requested.port && !requested.username && !requested.password) shopReturnTo=requested.toString();
    }catch{}

    body = JSON.stringify({
      email:
        String(
          form.get("email") ?? ""
        ),
      password:
        String(
          form.get("password") ?? ""
        ),
    });
  } else {
    body =
      await request.text();
  }

  try {
    const response =
      await backendFetch(
        "/api/v1/auth/login",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body,
        }
      );

    const data =
      await readBackendJson(
        response
      );

    if (!response.ok) {
      if (formMode) {
        const error =
          encodeURIComponent(
            data?.error ??
              "login_failed"
          );

        return new Response(
          null,
          {
            status: 303,
            headers: {
              Location:
                `/login?error=${error}${shopReturnTo?"&returnTo="+encodeURIComponent(shopReturnTo):""}`,
            },
          }
        );
      }

      return Response.json(
        data,
        {
          status:
            response.status,
        }
      );
    }

    await setAuthCookies(data);

    if (formMode) {
      return new Response(
        null,
        {
          status: 303,
          headers: {
            Location: shopReturnTo||"/collection",
          },
        }
      );
    }

    return Response.json({
      user: data.user,
    });
  } catch (error) {
    console.error(
      "Login backend unavailable",
      error
    );

    if (formMode) {
      return new Response(
        null,
        {
          status: 303,
          headers: {
            Location:
              `/login?error=server_unavailable${shopReturnTo?"&returnTo="+encodeURIComponent(shopReturnTo):""}`,
          },
        }
      );
    }

    return Response.json(
      {
        error: "server_unavailable",
      },
      {
        status: 503,
      }
    );
  }
}
