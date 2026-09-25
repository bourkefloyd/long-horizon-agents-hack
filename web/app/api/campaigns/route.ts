import { campaignApi } from "@/lib/campaign-api";

export async function GET() {
  return campaignApi("/campaigns");
}

export async function POST(request: Request) {
  return campaignApi("/campaigns", {
    method: "POST",
    body: await request.text(),
  });
}
