import type { Metadata } from "next";

import { AdDemoFeed } from "@/components/ad-demo-feed";

export const metadata: Metadata = {
  title: "Ad Demo Feed",
  description:
    "Swipe through vertical ad concepts while campaign signals become compact state.",
};

export default function FeedPage() {
  return <AdDemoFeed />;
}
