"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  CircleDot,
  FlaskConical,
  RefreshCw,
  Send,
  Sparkles,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  CampaignState,
  DecisionResult,
  EventType,
  NextDayBrief,
} from "@/lib/types";

const countColumns: { key: EventType; label: string }[] = [
  { key: "impression", label: "Impressions" },
  { key: "complete", label: "Completed" },
  { key: "cta_tap", label: "CTA taps" },
  { key: "install", label: "Installs" },
  { key: "skip", label: "Skips" },
];

async function responseMessage(response: Response) {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? `Request failed with status ${response.status}.`;
  } catch {
    return `Request failed with status ${response.status}.`;
  }
}

export function CampaignDashboard() {
  const [campaign, setCampaign] = useState<CampaignState | null>(null);
  const [brief, setBrief] = useState<NextDayBrief | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingAction, setPendingAction] = useState<
    "signal" | "decide" | null
  >(null);

  const loadCampaign = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/campaigns/demo/state", {
        cache: "no-store",
      });
      if (!response.ok) throw new Error(await responseMessage(response));
      setCampaign((await response.json()) as CampaignState);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Campaign state is unavailable.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCampaign();
  }, [loadCampaign]);

  const totalSignals = useMemo(() => {
    if (!campaign) return 0;
    return Object.values(campaign.counts).reduce(
      (campaignTotal, counts) =>
        campaignTotal +
        Object.values(counts).reduce(
          (variantTotal, count) => variantTotal + (count ?? 0),
          0,
        ),
      0,
    );
  }, [campaign]);

  async function sendSampleSignal() {
    setPendingAction("signal");
    setError(null);
    setNotice(null);

    try {
      const variantId =
        campaign?.variants[0] ?? `hook-${String.fromCharCode(97 + Math.floor(Math.random() * 3))}`;
      const response = await fetch("/api/signals", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          campaign_id: "demo",
          variant_id: variantId,
          event_type: "impression",
          timestamp: new Date().toISOString(),
        }),
      });
      if (!response.ok) throw new Error(await responseMessage(response));
      setNotice(
        `Queued an impression for ${variantId}. Decide to fold it into campaign memory.`,
      );
      await loadCampaign();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "The signal was not accepted.",
      );
    } finally {
      setPendingAction(null);
    }
  }

  async function decide() {
    setPendingAction("decide");
    setError(null);
    setNotice(null);

    try {
      const response = await fetch("/api/campaigns/demo/decide", {
        method: "POST",
      });
      if (!response.ok) throw new Error(await responseMessage(response));
      const result = (await response.json()) as DecisionResult;
      setCampaign(result.state);
      setBrief(result.next_day_brief);
      setNotice("Decision complete. The raw window is now compact campaign state.");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "The decision step failed.",
      );
    } finally {
      setPendingAction(null);
    }
  }

  if (loading) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-7xl items-center justify-center px-5">
        <div
          className="flex items-center gap-3 text-sm font-medium text-muted-foreground"
          role="status"
        >
          <RefreshCw className="size-4 animate-spin" aria-hidden="true" />
          Loading the demo campaign…
        </div>
      </main>
    );
  }

  if (error && !campaign) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-xl items-center px-5">
        <Card className="w-full border-destructive/30 bg-card/90">
          <CardHeader>
            <CardTitle>Campaign service unavailable</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => void loadCampaign(true)}>
              <RefreshCw aria-hidden="true" />
              Try again
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  const state = campaign!;
  const latestDecision = state.decisions.at(-1);
  const noiseFloor = state.aa_noise_floor.absolute_rate_difference;

  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-7 sm:px-8 sm:py-10">
      <header className="mb-10 flex flex-col gap-6 border-b border-border/70 pb-8 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <div className="mb-4 flex items-center gap-2">
            <Badge
              variant="outline"
              className="border-emerald-500/30 bg-emerald-500/10 text-emerald-800"
            >
              <CircleDot className="size-3 fill-emerald-500 text-emerald-500" />
              Server-side loop
            </Badge>
            <span className="font-mono text-xs text-muted-foreground">
              campaign/{state.campaign_id}
            </span>
          </div>
          <h1 className="text-balance text-4xl font-semibold tracking-[-0.04em] sm:text-6xl">
            Creative that gets{" "}
            <span className="text-orange-600">sharper overnight.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-pretty text-base leading-7 text-muted-foreground sm:text-lg">
            Run vertical video variants, fold today&apos;s signals into bounded
            memory, and hand tomorrow&apos;s generator one focused brief.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button
            variant="outline"
            size="lg"
            onClick={sendSampleSignal}
            disabled={pendingAction !== null}
          >
            {pendingAction === "signal" ? (
              <RefreshCw className="animate-spin" aria-hidden="true" />
            ) : (
              <Send aria-hidden="true" />
            )}
            Send sample signal
          </Button>
          <Button
            size="lg"
            onClick={decide}
            disabled={pendingAction !== null}
            className="bg-orange-600 text-white hover:bg-orange-700"
          >
            {pendingAction === "decide" ? (
              <RefreshCw className="animate-spin" aria-hidden="true" />
            ) : (
              <Sparkles aria-hidden="true" />
            )}
            Decide next day
          </Button>
        </div>
      </header>

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
          <div className="mb-6 flex items-center gap-2 rounded-xl border border-emerald-500/25 bg-emerald-500/8 px-4 py-3 text-sm text-emerald-900">
            <CheckCircle2 className="size-4 shrink-0" aria-hidden="true" />
            {notice}
          </div>
        ) : null}
      </div>

      <section
        aria-label="Campaign summary"
        className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
      >
        <MetricCard label="Live variants" value={state.variants.length} detail="9:16 creative cuts" />
        <MetricCard label="Folded signals" value={totalSignals} detail="Kept in compact counts" />
        <MetricCard label="Decisions" value={state.decisions.length} detail="Bounded to the latest 30" />
        <MetricCard label="Raw events dropped" value={state.dropped} detail="Stale context discarded" />
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.85fr)]">
        <Card className="overflow-hidden bg-card/90">
          <CardHeader className="border-b">
            <CardTitle>Variant performance</CardTitle>
            <CardDescription>
              Aggregated campaign memory, not an ever-growing event stream.
            </CardDescription>
            <CardAction>
              <Badge variant="secondary">{state.variants.length} active</Badge>
            </CardAction>
          </CardHeader>
          <CardContent className="p-0">
            {state.variants.length === 0 ? (
              <EmptyVariants />
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="min-w-40 pl-6">Variant</TableHead>
                      {countColumns.map((column) => (
                        <TableHead key={column.key} className="text-right">
                          {column.label}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {state.variants.map((variant) => {
                      const isWinner =
                        latestDecision?.winner_variant_id === variant;
                      return (
                        <TableRow key={variant}>
                          <TableCell className="pl-6 font-medium">
                            <div className="flex items-center gap-2">
                              {variant}
                              {isWinner ? (
                                <Badge className="bg-orange-600 text-white">
                                  Keep
                                </Badge>
                              ) : null}
                            </div>
                          </TableCell>
                          {countColumns.map((column) => (
                            <TableCell
                              key={column.key}
                              className="text-right font-mono tabular-nums"
                            >
                              {state.counts[variant]?.[column.key] ?? 0}
                            </TableCell>
                          ))}
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="grid gap-6">
          <Card className="bg-zinc-950 text-zinc-50">
            <CardHeader>
              <div className="mb-2 flex size-10 items-center justify-center rounded-xl bg-orange-500 text-white">
                <FlaskConical className="size-5" aria-hidden="true" />
              </div>
              <CardTitle>A/A noise floor</CardTitle>
              <CardDescription className="text-zinc-400">
                A/B lift must clear this baseline before it is trusted.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold tracking-tight">
                {noiseFloor === null
                  ? "Not estimated"
                  : `${(noiseFloor * 100).toFixed(2)}%`}
              </p>
              <p className="mt-3 text-sm leading-6 text-zinc-400">
                {state.aa_noise_floor.note}
              </p>
            </CardContent>
          </Card>

          <Card className="bg-card/90">
            <CardHeader>
              <CardTitle>Latest decision</CardTitle>
              <CardDescription>
                The retained choice and the reason behind it.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {latestDecision ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-sm text-muted-foreground">Keep</span>
                    <Badge variant="secondary">
                      {latestDecision.winner_variant_id ?? "No variant yet"}
                    </Badge>
                  </div>
                  <p className="text-sm leading-6">
                    {latestDecision.rationale}
                  </p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {new Intl.DateTimeFormat("en", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    }).format(new Date(latestDecision.decided_at))}
                  </p>
                </div>
              ) : (
                <p className="text-sm leading-6 text-muted-foreground">
                  No decision has been made. Send a sample signal, then run the
                  decision step to create the first brief.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <section className="mt-6" aria-labelledby="next-day-title">
        <Card className="overflow-hidden border-orange-200 bg-orange-50/80">
          <CardHeader>
            <Badge className="mb-2 w-fit bg-orange-600 text-white">
              Day +1 handoff
            </Badge>
            <CardTitle id="next-day-title">Next-day generation brief</CardTitle>
            <CardDescription>
              One compact instruction replaces yesterday&apos;s raw event history.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {brief ? (
              <div className="grid gap-5 md:grid-cols-[180px_1fr]">
                <div>
                  <p className="text-xs font-medium uppercase tracking-widest text-orange-800/70">
                    Keep
                  </p>
                  <p className="mt-2 font-semibold">
                    {brief.keep_variant_id ?? "Collect more traffic"}
                  </p>
                </div>
                <div className="border-orange-200 md:border-l md:pl-6">
                  <p className="text-xs font-medium uppercase tracking-widest text-orange-800/70">
                    Generator instruction
                  </p>
                  <p className="mt-2 max-w-3xl text-base leading-7">
                    {brief.instruction}
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-4 text-sm text-orange-950/70 sm:flex-row sm:items-center sm:justify-between">
                <p>Run “Decide next day” to turn current signals into a brief.</p>
                <ArrowRight className="hidden size-5 sm:block" aria-hidden="true" />
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}

function MetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: number;
  detail: string;
}) {
  return (
    <Card className="gap-3 bg-card/90 py-5">
      <CardHeader className="px-5">
        <CardDescription>{label}</CardDescription>
        <CardTitle className="font-mono text-3xl tabular-nums">{value}</CardTitle>
      </CardHeader>
      <CardContent className="px-5 text-xs text-muted-foreground">
        {detail}
      </CardContent>
    </Card>
  );
}

function EmptyVariants() {
  return (
    <div className="flex min-h-72 flex-col items-center justify-center px-6 text-center">
      <div className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-muted">
        <Sparkles className="size-5 text-muted-foreground" aria-hidden="true" />
      </div>
      <h2 className="font-semibold">No folded variants yet</h2>
      <p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
        Send a sample signal and decide the campaign. The service will fold that
        event into the first bounded variant row.
      </p>
    </div>
  );
}
