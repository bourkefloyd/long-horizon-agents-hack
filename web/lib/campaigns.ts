import type { CampaignState } from "@/lib/types";

export type CampaignStatus = "draft" | "queued" | "generating" | "live";

export interface CampaignInput {
  name: string;
  brief: string;
  vertical: string;
  geo: string;
  audience: string;
  dims: string;
}

export interface Campaign extends CampaignInput {
  id: string;
  status: CampaignStatus;
  created_at: string;
  issue_url: string | null;
}

export interface CampaignDetail extends Campaign {
  state: CampaignState;
}

export interface QueueResult {
  campaign: Campaign;
  message: string;
}

export const DIMS_OPTIONS = ["9:16", "1:1", "16:9", "4:5"] as const;

export const VERTICAL_OPTIONS = [
  "Mobile games",
  "Food & beverage",
  "Retail",
  "Local services",
  "Events",
  "Consumer apps",
] as const;

export const EXAMPLE_CAMPAIGN: CampaignInput = {
  name: "SF Coffee Launch",
  brief: "Casual mobile game cross-promo for SF coffee lovers",
  vertical: "Mobile games",
  geo: "San Francisco",
  audience: "Coffee lovers, 21-40, commute by transit",
  dims: "9:16",
};

export const STATUS_LABELS: Record<CampaignStatus, string> = {
  draft: "Draft",
  queued: "Queued",
  generating: "Generating",
  live: "Live",
};

async function responseMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as {
      detail?: string | { msg?: string }[];
    };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      return body.detail[0].msg;
    }
  } catch {
    // fall through to the status text
  }
  return `Request failed with status ${response.status}.`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: "no-store", ...init });
  if (!response.ok) throw new Error(await responseMessage(response));
  return (await response.json()) as T;
}

export function listCampaigns(): Promise<Campaign[]> {
  return request<Campaign[]>("/api/campaigns");
}

export function getCampaign(id: string): Promise<CampaignDetail> {
  return request<CampaignDetail>(`/api/campaigns/${encodeURIComponent(id)}`);
}

export function createCampaign(input: CampaignInput): Promise<Campaign> {
  return request<Campaign>("/api/campaigns", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function queueCampaign(id: string): Promise<QueueResult> {
  return request<QueueResult>(
    `/api/campaigns/${encodeURIComponent(id)}/queue`,
    { method: "POST" },
  );
}

export function formatCreatedAt(iso: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}
