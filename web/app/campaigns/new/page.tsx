import type { Metadata } from "next";

import { NewCampaignForm } from "@/components/new-campaign-form";

export const metadata: Metadata = {
  title: "New campaign · Long Horizon",
  description: "Write a brief and queue the campaign-gen agent.",
};

export default function NewCampaignPage() {
  return <NewCampaignForm />;
}
