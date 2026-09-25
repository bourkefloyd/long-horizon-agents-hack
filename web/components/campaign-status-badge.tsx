import { cn } from "cn";

import { Badge } from "@/components/ui/badge";
import { STATUS_LABELS, type CampaignStatus } from "@/lib/campaigns";

const statusStyles: Record<CampaignStatus, string> = {
  draft: "border-border bg-muted text-muted-foreground",
  queued: "border-amber-500/30 bg-amber-500/10 text-amber-900",
  generating: "border-sky-500/30 bg-sky-500/10 text-sky-900",
  live: "border-emerald-500/30 bg-emerald-500/10 text-emerald-800",
};

export function CampaignStatusBadge({
  status,
  className,
}: {
  status: CampaignStatus;
  className?: string;
}) {
  return (
    <Badge variant="outline" className={cn(statusStyles[status], className)}>
      {STATUS_LABELS[status]}
    </Badge>
  );
}
