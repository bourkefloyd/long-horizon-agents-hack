import { campaignApi } from "@/lib/campaign-api";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return campaignApi(`/campaigns/${encodeURIComponent(id)}/state`);
}
