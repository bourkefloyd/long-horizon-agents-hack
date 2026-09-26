/**
 * Tinybird agent event memory. Server-side only (route handlers / server components):
 * the token must never reach the browser.
 *
 *   await emit("sf-coffee-launch", "campaign-gen", "variant_generated", { hook }, runId, "v1", 0.03);
 *   const rows = await read("sf-coffee-launch", "2026-09-25T00:00:00Z");
 *
 * Env: TINYBIRD_API_KEY (required), TINYBIRD_HOST (default https://api.tinybird.co).
 */

const DATASOURCE = "agent_events";

export type AgentEvent = {
  ts: string;
  campaign_id: string;
  agent: string;
  run_id: string;
  event_type: string;
  variant_id: string | null;
  payload: string;
  cost_usd: number | null;
};

export function tinybirdConfigured(): boolean {
  return Boolean(process.env.TINYBIRD_API_KEY);
}

function host(): string {
  return (process.env.TINYBIRD_HOST ?? "https://api.tinybird.co").replace(/\/$/, "");
}

function token(): string {
  const value = process.env.TINYBIRD_API_KEY;
  if (!value) throw new Error("TINYBIRD_API_KEY is not set");
  return value;
}

function timestamp(value?: Date | string): string {
  const date = value instanceof Date ? value : value ? new Date(value) : new Date();
  return date.toISOString().slice(0, 19).replace("T", " ");
}

export async function emit(
  campaignId: string,
  agent: string,
  eventType: string,
  payload: unknown = {},
  runId: string = crypto.randomUUID().slice(0, 12),
  variantId: string | null = null,
  costUsd: number | null = null,
  options: { ts?: Date | string; wait?: boolean } = {},
): Promise<string> {
  const row = {
    ts: timestamp(options.ts),
    campaign_id: campaignId,
    agent,
    run_id: runId,
    event_type: eventType,
    variant_id: variantId,
    payload: JSON.stringify(payload ?? {}),
    cost_usd: costUsd,
  };
  const query = new URLSearchParams({ name: DATASOURCE });
  if (options.wait) query.set("wait", "true");
  const response = await fetch(`${host()}/v0/events?${query}`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${token()}`,
      "content-type": "application/x-ndjson",
    },
    body: `${JSON.stringify(row)}\n`,
  });
  if (response.status !== 200 && response.status !== 202) {
    throw new Error(`Tinybird Events API returned ${response.status}: ${(await response.text()).slice(0, 300)}`);
  }
  return runId;
}

async function pipe<T>(name: string, params: Record<string, string | number | undefined | null>): Promise<T[]> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) query.set(key, String(value));
  }
  const response = await fetch(`${host()}/v0/pipes/${name}.json?${query}`, {
    headers: { authorization: `Bearer ${token()}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Tinybird pipe ${name} returned ${response.status}: ${(await response.text()).slice(0, 300)}`);
  }
  const body = (await response.json()) as { data?: T[] };
  return body.data ?? [];
}

export async function read(
  campaignId: string,
  since?: Date | string,
  agent?: string,
  limit = 200,
): Promise<AgentEvent[]> {
  return pipe<AgentEvent>("campaign_events", {
    campaign_id: campaignId,
    since: since instanceof Date ? timestamp(since) : since,
    agent,
    limit,
  });
}

export type AgentSummaryRow = {
  agent: string;
  event_type: string;
  events: number;
  cost_usd: number;
  first_ts: string;
  last_ts: string;
};

export async function summary(campaignId: string): Promise<AgentSummaryRow[]> {
  return pipe<AgentSummaryRow>("campaign_summary", { campaign_id: campaignId });
}
