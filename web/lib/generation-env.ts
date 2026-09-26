export type GenerationProviderStatus = {
  configured: boolean;
  detail: string;
};

export type GenerationStatus = {
  nimble: GenerationProviderStatus;
  bfl: GenerationProviderStatus;
  liquid: GenerationProviderStatus;
};

export function readGenerationStatus(): GenerationStatus {
  const nimbleKey = process.env.NIMBLE_API_KEY?.trim();
  const bflKey =
    process.env.BFL_API_KEY?.trim() ||
    process.env.BLACK_FOREST?.trim();
  const campaignBase = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

  return {
    nimble: {
      configured: Boolean(nimbleKey),
      detail: nimbleKey
        ? "Nimble search API key is configured on the web service."
        : "Set NIMBLE_API_KEY on Cloud Run to run live discover-news calls.",
    },
    bfl: {
      configured: Boolean(bflKey),
      detail: bflKey
        ? "Black Forest Labs key is configured for FLUX 3 video jobs."
        : "Set BFL_API_KEY or BLACK_FOREST on the web service to submit renders.",
    },
    liquid: {
      configured: Boolean(campaignBase),
      detail: campaignBase
        ? "Campaign service reachable for Liquid-style fold + next-day brief."
        : "Set NEXT_PUBLIC_API_BASE_URL to the campaign service URL.",
    },
  };
}
