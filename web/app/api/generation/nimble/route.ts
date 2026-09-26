const NIMBLE_BASE =
  process.env.NIMBLE_BASE_URL?.replace(/\/$/, "") ??
  "https://sdk.nimbleway.com";

type Story = {
  title: string;
  url: string;
  source: string;
  snippet: string;
};

function mockStories(market: string): Story[] {
  return [
    {
      title: `${market} food festival draws huge weekend crowds`,
      url: "https://example.com/local-food-festival",
      source: "Mock Local News",
      snippet:
        "A lively neighborhood food event became one of the area's most shared local stories.",
    },
    {
      title: `${market} baseball fans celebrate a dramatic late-game win`,
      url: "https://example.com/local-sports-win",
      source: "Mock Sports Desk",
      snippet:
        "Fans shared clips from a dramatic finish and packed local hangouts after the game.",
    },
    {
      title: `New public art installation becomes a selfie spot in ${market}`,
      url: "https://example.com/public-art",
      source: "Mock Culture",
      snippet:
        "A colorful public art installation is trending as a cheerful photo backdrop.",
    },
  ];
}

function normalizeStories(payload: unknown): Story[] {
  if (!payload || typeof payload !== "object") return [];
  const record = payload as Record<string, unknown>;
  const candidates =
    record.results ?? record.items ?? record.data ?? record.organic_results ?? [];
  if (!Array.isArray(candidates)) return [];

  const stories: Story[] = [];
  for (const item of candidates) {
    if (!item || typeof item !== "object") continue;
    const row = item as Record<string, unknown>;
    const title = String(row.title ?? row.name ?? "").trim();
    const url = String(row.url ?? row.link ?? "").trim();
    const snippet = String(
      row.snippet ?? row.description ?? row.summary ?? "",
    ).trim();
    const source = String(
      row.source ?? row.publisher ?? row.domain ?? "",
    ).trim();
    if (!title || !url) continue;
    stories.push({ title, url, source, snippet });
  }
  return stories;
}

export async function POST(request: Request) {
  let market = "San Francisco";
  let limit = 5;
  let useMock = false;

  try {
    const body = (await request.json()) as {
      market?: string;
      limit?: number;
      use_mock?: boolean;
    };
    if (body.market?.trim()) market = body.market.trim();
    if (typeof body.limit === "number" && body.limit > 0) {
      limit = Math.min(body.limit, 10);
    }
    useMock = body.use_mock === true;
  } catch {
    // defaults are fine for demo POSTs
  }

  const apiKey = process.env.NIMBLE_API_KEY?.trim();
  if (!apiKey || useMock) {
    return Response.json({
      mode: "mock" as const,
      market,
      stories: mockStories(market).slice(0, limit),
    });
  }

  const query =
    `viral local news stories in ${market} from the past week. ` +
    "Prioritize widely shared community, culture, sports, food, events, weather-light, " +
    "entertainment, and human-interest stories. Avoid tragedy, violent crime, politics, " +
    "lawsuits, disasters, and health emergencies.";

  try {
    const response = await fetch(`${NIMBLE_BASE}/v2/search`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        focus: "news",
        max_results: limit,
        search_depth: "standard",
      }),
      cache: "no-store",
    });

    if (!response.ok) {
      const detail = await response.text();
      return Response.json(
        { detail: `Nimble search failed (${response.status}): ${detail}` },
        { status: 502 },
      );
    }

    const payload: unknown = await response.json();
    const stories = normalizeStories(payload).slice(0, limit);
    return Response.json({
      mode: "live" as const,
      market,
      stories,
    });
  } catch {
    return Response.json(
      { detail: "Could not reach the Nimble search API." },
      { status: 502 },
    );
  }
}
