const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");

export async function campaignApi(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  if (!apiBaseUrl) {
    return Response.json(
      {
        detail:
          "NEXT_PUBLIC_API_BASE_URL is not configured. Set it to the campaign service URL.",
      },
      { status: 503 },
    );
  }

  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        "content-type": "application/json",
        ...init?.headers,
      },
    });

    return new Response(response.body, {
      status: response.status,
      headers: {
        "content-type":
          response.headers.get("content-type") ?? "application/json",
      },
    });
  } catch {
    return Response.json(
      { detail: "The campaign service could not be reached." },
      { status: 502 },
    );
  }
}
