import type { Metadata } from "next";

import { CampaignDetail } from "@/components/campaign-detail";

export const metadata: Metadata = {
  title: "Campaign · Long Horizon",
  description: "Campaign brief, generation status, and task issue.",
};

export default async function CampaignPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <CampaignDetail id={id} />;
}
