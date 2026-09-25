const BFL_BASE =
  process.env.BFL_BASE_URL?.replace(/\/$/, "") ?? "https://api.bfl.ai";

export async function POST(request: Request) {
  let hook = "";
  let script = "";
  let generate = false;

  try {
    const body = (await request.json()) as {
      hook?: string;
      script?: string;
      generate?: boolean;
    };
    hook = body.hook?.trim() ?? "";
    script = body.script?.trim() ?? "";
    generate = body.generate === true;
  } catch {
    return Response.json({ detail: "Expected JSON body." }, { status: 400 });
  }

  if (!hook && !script) {
    return Response.json(
      { detail: "Provide hook and/or script for a FLUX 3 preview." },
      { status: 400 },
    );
  }

  const payload = {
    mode: "t2v" as const,
    prompt: script || hook,
    duration: 10,
    aspect_ratio: "9:16",
    resolution: "hd",
    generate_audio: true,
  };

  const apiKey =
    process.env.BFL_API_KEY?.trim() || process.env.BLACK_FOREST?.trim();

  if (!generate || !apiKey) {
    return Response.json({
      mode: "preview" as const,
      endpoint: `${BFL_BASE}/v1/flux-3-video`,
      configured: Boolean(apiKey),
      payload,
    });
  }

  try {
    const response = await fetch(`${BFL_BASE}/v1/flux-3-video`, {
      method: "POST",
      headers: {
        accept: "application/json",
        "x-key": apiKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    const body: unknown = await response.json().catch(() => ({}));
    if (!response.ok) {
      return Response.json(
        {
          detail: "BFL rejected the render request.",
          status: response.status,
          body,
        },
        { status: 502 },
      );
    }

    return Response.json({
      mode: "submitted" as const,
      endpoint: `${BFL_BASE}/v1/flux-3-video`,
      result: body,
    });
  } catch {
    return Response.json(
      { detail: "Could not reach the Black Forest Labs API." },
      { status: 502 },
    );
  }
}
