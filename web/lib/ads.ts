export const DEFAULT_ADS_MANIFEST_URL =
  "https://storage.googleapis.com/lh-ads-assets-205515555985/manifest.json";

export type AdMediaType = "video" | "image" | "playable" | "script";

export interface Ad {
  id: string;
  campaign_id: string;
  variant_id: string;
  hook: string;
  cta: string;
  media_type: AdMediaType;
  media_url: string;
  poster_url?: string;
  duration_s?: number;
  aspect: "9:16";
  script?: string;
  targeting: {
    audience?: string[];
    geo?: string[];
    weight: number;
    active: boolean;
  };
  source: {
    agent: string;
    generated_at: string;
    brief_ref?: string;
  };
}

export interface AdManifest {
  version: 1;
  updated_at: string;
  ads: Ad[];
}

export interface AdContext {
  audience?: string | string[];
  geo?: string;
  random?: () => number;
}

export async function fetchAdManifest(): Promise<AdManifest> {
  const url =
    process.env.NEXT_PUBLIC_ADS_MANIFEST_URL ?? DEFAULT_ADS_MANIFEST_URL;
  const response = await fetch(url, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(
      `Could not fetch ad manifest (${response.status} ${response.statusText})`,
    );
  }

  const manifest: unknown = await response.json();
  if (
    !manifest ||
    typeof manifest !== "object" ||
    (manifest as Partial<AdManifest>).version !== 1 ||
    !Array.isArray((manifest as Partial<AdManifest>).ads)
  ) {
    throw new Error("Ad manifest has an unsupported shape or version");
  }

  return manifest as AdManifest;
}

export function pickAd(
  manifest: AdManifest,
  context: AdContext = {},
): Ad | null {
  const audiences = (
    Array.isArray(context.audience) ? context.audience : [context.audience]
  )
    .filter((value): value is string => Boolean(value))
    .map(normalize);
  const geo = context.geo ? normalize(context.geo) : undefined;

  const eligible = manifest.ads.filter((ad) => {
    if (!ad.targeting.active || ad.targeting.weight <= 0) return false;

    const targetAudiences = ad.targeting.audience?.map(normalize) ?? [];
    if (
      audiences.length > 0 &&
      targetAudiences.length > 0 &&
      !audiences.some((audience) => targetAudiences.includes(audience))
    ) {
      return false;
    }

    const targetGeos = ad.targeting.geo?.map(normalize) ?? [];
    return !(geo && targetGeos.length > 0 && !targetGeos.includes(geo));
  });

  const totalWeight = eligible.reduce(
    (sum, ad) => sum + ad.targeting.weight,
    0,
  );
  if (totalWeight <= 0) return null;

  const random = context.random ?? Math.random;
  let cursor = Math.min(Math.max(random(), 0), 1 - Number.EPSILON) * totalWeight;
  for (const ad of eligible) {
    cursor -= ad.targeting.weight;
    if (cursor < 0) return ad;
  }

  return eligible.at(-1) ?? null;
}

function normalize(value: string): string {
  return value.trim().toLowerCase();
}
