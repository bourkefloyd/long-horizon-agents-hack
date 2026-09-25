import { campaignApi } from "@/lib/campaign-api";

export async function GET() {
  return campaignApi("/campaigns/demo/state");
}
