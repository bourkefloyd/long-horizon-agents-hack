export type EventType =
  | "impression"
  | "q25"
  | "q50"
  | "q75"
  | "complete"
  | "skip"
  | "cta_tap"
  | "install";

export type VariantCounts = Partial<Record<EventType, number>>;

export interface CampaignDecision {
  decided_at: string;
  winner_variant_id: string | null;
  rationale: string;
}

export interface CampaignState {
  campaign_id: string;
  variants: string[];
  counts: Record<string, VariantCounts>;
  aa_noise_floor: {
    status: string;
    absolute_rate_difference: number | null;
    note: string;
  };
  decisions: CampaignDecision[];
  dropped: number;
}

export interface NextDayBrief {
  campaign_id: string;
  keep_variant_id: string | null;
  instruction: string;
}

export interface DecisionResult {
  state: CampaignState;
  next_day_brief: NextDayBrief;
}
