import { campaignApi } from "@/lib/campaign-api";

/** Liquid-style fold: proxy to the campaign service decide step. */
export async function POST() {
  return campaignApi("/campaigns/demo/decide", { method: "POST" });
}
