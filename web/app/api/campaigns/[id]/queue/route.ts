import { campaignApi } from "@/lib/campaign-api";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return campaignApi(`/campaigns/${encodeURIComponent(id)}/queue`, {
    method: "POST",
  });
}
