import { campaignApi } from "@/lib/campaign-api";

export async function POST() {
  return campaignApi("/campaigns/demo/decide", { method: "POST" });
}
