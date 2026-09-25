import { campaignApi } from "@/lib/campaign-api";

export async function POST(request: Request) {
  return campaignApi("/signals", {
    method: "POST",
    body: await request.text(),
  });
}
