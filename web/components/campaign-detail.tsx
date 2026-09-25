"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  ExternalLink,
  PlaySquare,
  RefreshCw,
  Sparkles,
} from "lucide-react";

import { CampaignStatusBadge } from "@/components/campaign-status-badge";
import { CampaignsPageShell } from "@/components/campaigns-page-shell";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  formatCreatedAt,
  getCampaign,
  queueCampaign,
  type CampaignDetail as CampaignDetailRecord,
} from "@/lib/campaigns";

export function CampaignDetail({ id }: { id: string }) {
  const [campaign, setCampaign] = useState<CampaignDetailRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [queueing, setQueueing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setCampaign(await getCampaign(id));
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "The campaign is unavailable.",
      );
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    getCampaign(id)
      .then((record) => {
        if (!cancelled) setCampaign(record);
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(
            caught instanceof Error
              ? caught.message
              : "The campaign is unavailable.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function generate() {
    if (!campaign) return;
    setQueueing(true);
    setError(null);
    setNotice(null);
    try {
      const result = await queueCampaign(campaign.id);
      setCampaign({ ...campaign, ...result.campaign });
      setNotice(result.message);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "The campaign was not queued.",
      );
    } finally {
      setQueueing(false);
    }
  }

  if (loading && campaign === null) {
    return (
      <CampaignsPageShell
        crumbs={[{ label: "Campaigns", href: "/campaigns" }, { label: id }]}
        title={<span className="font-mono text-2xl">{id}</span>}
        description="Loading the campaign record…"
      >
        <div
          className="flex min-h-48 items-center justify-center gap-3 text-sm font-medium text-muted-foreground"
          role="status"
        >
          <RefreshCw className="size-4 animate-spin" aria-hidden="true" />
          Loading campaign…
        </div>
      </CampaignsPageShell>
    );
  }

  if (campaign === null) {
    return (
      <CampaignsPageShell
        crumbs={[{ label: "Campaigns", href: "/campaigns" }, { label: id }]}
        title="Campaign not found"
        description={error ?? "This campaign id does not exist."}
      >
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button variant="outline" size="lg" onClick={() => void load()}>
            <RefreshCw aria-hidden="true" />
            Try again
          </Button>
          <Link
            href="/campaigns"
            className={buttonVariants({ size: "lg", variant: "outline" })}
          >
            Back to campaigns
          </Link>
        </div>
      </CampaignsPageShell>
    );
  }

  const canGenerate = campaign.issue_url === null;

  return (
    <CampaignsPageShell
      crumbs={[
        { label: "Campaigns", href: "/campaigns" },
        { label: campaign.name },
      ]}
      title={
        <span className="flex flex-wrap items-center gap-3">
          {campaign.name}
          <CampaignStatusBadge status={campaign.status} className="h-6 text-sm" />
        </span>
      }
      description={
        <>
          <span className="font-mono text-xs">{campaign.id}</span> · created{" "}
          {formatCreatedAt(campaign.created_at)}
        </>
      }
      actions={
        <>
          <Link
            href={`/feed?campaign=${encodeURIComponent(campaign.id)}`}
            className={buttonVariants({ size: "lg", variant: "outline" })}
          >
            <PlaySquare aria-hidden="true" />
            View feed
          </Link>
          <Button
            variant="outline"
            size="lg"
            onClick={() => void load()}
            disabled={loading || queueing}
          >
            <RefreshCw
              className={loading ? "animate-spin" : undefined}
              aria-hidden="true"
            />
            Refresh
          </Button>
          {campaign.issue_url ? (
            <a
              href={campaign.issue_url}
              target="_blank"
              rel="noreferrer"
              className={buttonVariants({ size: "lg" }) + " bg-orange-600 text-white hover:bg-orange-700"}
            >
              <ExternalLink aria-hidden="true" />
              Open task issue
            </a>
          ) : (
            <Button
              size="lg"
              onClick={generate}
              disabled={queueing}
              className="bg-orange-600 text-white hover:bg-orange-700"
            >
              {queueing ? (
                <RefreshCw className="animate-spin" aria-hidden="true" />
              ) : (
                <Sparkles aria-hidden="true" />
              )}
              {canGenerate && campaign.status === "queued"
                ? "Retry generate"
                : "Generate"}
            </Button>
          )}
        </>
      }
    >
      <div aria-live="polite">
        {error ? (
          <div
            className="mb-6 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
            role="alert"
          >
            {error}
          </div>
        ) : null}
        {notice ? (
          <div className="mb-6 flex items-start gap-2 rounded-xl border border-emerald-500/25 bg-emerald-500/8 px-4 py-3 text-sm text-emerald-900">
            <CheckCircle2 className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            {notice}
          </div>
        ) : null}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(280px,0.8fr)]">
        <Card className="bg-card/90">
          <CardHeader>
            <CardTitle>Brief</CardTitle>
            <CardDescription>
              What the campaign-gen agent receives in its task issue.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <p className="text-base leading-7">{campaign.brief}</p>
            <dl className="grid gap-4 sm:grid-cols-2">
              <Detail label="Vertical" value={campaign.vertical} />
              <Detail label="Market" value={campaign.geo} />
              <Detail label="Audience" value={campaign.audience} />
              <Detail label="Aspect ratio" value={campaign.dims} />
            </dl>
          </CardContent>
        </Card>

        <div className="grid gap-6">
          <Card className="bg-zinc-950 text-zinc-50">
            <CardHeader>
              <CardTitle>Generation</CardTitle>
              <CardDescription className="text-zinc-400">
                {campaign.issue_url
                  ? "The agent is working from this issue."
                  : campaign.status === "queued"
                    ? "Queued without a task issue."
                    : "Not queued yet."}
              </CardDescription>
            </CardHeader>
            <CardContent className="text-sm leading-6 text-zinc-300">
              {campaign.issue_url ? (
                <a
                  href={campaign.issue_url}
                  target="_blank"
                  rel="noreferrer"
                  className="break-all font-mono text-xs text-orange-300 hover:underline"
                >
                  {campaign.issue_url}
                </a>
              ) : campaign.status === "queued" ? (
                <p>
                  The service had no GitHub token, so no issue was opened. Mount the
                  LH_GITHUB_TOKEN secret on the Cloud Run service, then retry.
                </p>
              ) : (
                <p>
                  Generate opens an issue labeled{" "}
                  <code className="text-zinc-100">lh:campaign-gen</code>. The agent
                  writes creative to{" "}
                  <code className="text-zinc-100">cdn/staging/{campaign.id}/</code>.
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="bg-card/90">
            <CardHeader>
              <CardTitle>Signals</CardTitle>
              <CardDescription>
                Folded state for this campaign id.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-3 gap-4">
                <Detail
                  label="Variants"
                  value={String(campaign.state.variants.length)}
                  mono
                />
                <Detail
                  label="Decisions"
                  value={String(campaign.state.decisions.length)}
                  mono
                />
                <Detail label="Dropped" value={String(campaign.state.dropped)} mono />
              </dl>
            </CardContent>
          </Card>
        </div>
      </div>
    </CampaignsPageShell>
  );
}

function Detail({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </dt>
      <dd className={mono ? "mt-1 font-mono text-2xl tabular-nums" : "mt-1 text-sm"}>
        {value}
      </dd>
    </div>
  );
}
