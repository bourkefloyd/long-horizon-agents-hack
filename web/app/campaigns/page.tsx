import type { Metadata } from "next";

import { CampaignList } from "@/components/campaign-list";

export const metadata: Metadata = {
  title: "Campaigns · Long Horizon",
  description:
    "Create campaigns and queue the campaign-gen agent to produce vertical creative.",
};

export default function CampaignsPage() {
  return <CampaignList />;
}
