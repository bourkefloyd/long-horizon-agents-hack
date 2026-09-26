import type { Metadata } from "next";

import { AdDemoFeed } from "@/components/ad-demo-feed";

export const metadata: Metadata = {
  title: "Ad Demo Feed",
  description:
    "Swipe through vertical ad concepts while campaign signals become compact state.",
};

export default async function FeedPage({
  searchParams,
}: {
  searchParams: Promise<{ campaign?: string | string[] }>;
}) {
  const { campaign } = await searchParams;
  const campaignId = (Array.isArray(campaign) ? campaign[0] : campaign)?.trim();
  return <AdDemoFeed campaignId={campaignId || undefined} />;
}
