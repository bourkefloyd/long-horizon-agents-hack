"use client";

import Link from "next/link";
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Check,
  ExternalLink,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { localAdManifest, type AdManifestItem } from "@/content/ads";
import type { CampaignState, EventType, VariantCounts } from "@/lib/types";

const ads = localAdManifest.filter((ad) => ad.targeting.active);
const adStyles = [
  { brand: "Sightglass Coffee", from: "#071b2b", via: "#31515a", to: "#d5b887" },
  { brand: "Tartine Bakery", from: "#15354a", via: "#df8d55", to: "#f6d991" },
  { brand: "Bi-Rite Creamery", from: "#59284f", via: "#df5b78", to: "#ffcf8b" },
  { brand: "Dandelion Chocolate", from: "#21120d", via: "#75452d", to: "#d9ad74" },
  { brand: "Boudin Bakery", from: "#26343f", via: "#6e8791", to: "#e6b968" },
];
type AdStyle = (typeof adStyles)[number];

function dwellEventsFor(ad: AdManifestItem) {
  const durationMs = (ad.duration_s ?? 10) * 1_000;
  return [
    { delay: durationMs * 0.25, event: "q25" as const },
    { delay: durationMs * 0.5, event: "q50" as const },
    { delay: durationMs * 0.75, event: "q75" as const },
    { delay: durationMs, event: "complete" as const },
  ];
}

type SignalStatus = {
  kind: "sending" | "accepted" | "error";
  message: string;
};

async function responseMessage(response: Response) {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? `Request failed with status ${response.status}.`;
  } catch {
    return `Request failed with status ${response.status}.`;
  }
}

async function getCampaignState() {
  const response = await fetch("/api/campaigns/demo/state", {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await responseMessage(response));
  return (await response.json()) as CampaignState;
}

export function AdDemoFeed() {
  const itemRefs = useRef<(HTMLElement | null)[]>([]);
  const visibilityRatios = useRef(new Map<number, number>());
  const emittedSignals = useRef(new Set<string>());
  const activeSession = useRef<{
    campaignId: string;
    variant: string;
    startedAt: number;
    earlySkipMs: number;
  } | null>(null);
  const dwellTimers = useRef<number[]>([]);

  const [activeIndex, setActiveIndex] = useState(0);
  const [campaign, setCampaign] = useState<CampaignState | null>(null);
  const [stateLoading, setStateLoading] = useState(true);
  const [stateError, setStateError] = useState<string | null>(null);
  const [signalStatuses, setSignalStatuses] = useState<
    Record<string, SignalStatus>
  >({});

  const loadState = useCallback(async () => {
    setStateLoading(true);
    setStateError(null);
    try {
      setCampaign(await getCampaignState());
    } catch (caught) {
      setStateError(
        caught instanceof Error
          ? caught.message
          : "Campaign state is unavailable.",
      );
    } finally {
      setStateLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadState();
  }, [loadState]);

  const emitSignal = useCallback(
    async (
      campaignId: string,
      variant: string,
      eventType: EventType,
    ) => {
      const signalKey = `${campaignId}:${variant}:${eventType}`;
      if (emittedSignals.current.has(signalKey)) return;
      emittedSignals.current.add(signalKey);
      setSignalStatuses((current) => ({
        ...current,
        [variant]: {
          kind: "sending",
          message: `Sending ${eventType.replace("_", " ")}…`,
        },
      }));

      try {
        const response = await fetch("/api/signals", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            campaign_id: campaignId,
            variant_id: variant,
            event_type: eventType,
            timestamp: new Date().toISOString(),
          }),
          keepalive: true,
        });
        if (!response.ok) throw new Error(await responseMessage(response));
        setSignalStatuses((current) => ({
          ...current,
          [variant]: {
            kind: "accepted",
            message: `${eventType.replace("_", " ")} accepted`,
          },
        }));
      } catch (caught) {
        emittedSignals.current.delete(signalKey);
        setSignalStatuses((current) => ({
          ...current,
          [variant]: {
            kind: "error",
            message:
              caught instanceof Error
                ? caught.message
                : "Signal was not accepted.",
          },
        }));
      }
    },
    [],
  );

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const index = Number((entry.target as HTMLElement).dataset.index);
          visibilityRatios.current.set(
            index,
            entry.isIntersecting ? entry.intersectionRatio : 0,
          );
        }

        let nextIndex = activeIndex;
        let highestRatio = 0.35;
        for (const [index, ratio] of visibilityRatios.current) {
          if (ratio > highestRatio) {
            highestRatio = ratio;
            nextIndex = index;
          }
        }
        setActiveIndex(nextIndex);
      },
      { threshold: [0, 0.35, 0.55, 0.75] },
    );

    for (const item of itemRefs.current) {
      if (item) observer.observe(item);
    }
    return () => observer.disconnect();
  }, [activeIndex]);

  useEffect(() => {
    const ad = ads[activeIndex];
    const previous = activeSession.current;
    if (previous && previous.variant !== ad.variant_id) {
      const elapsed = performance.now() - previous.startedAt;
      if (elapsed < previous.earlySkipMs) {
        void emitSignal(previous.campaignId, previous.variant, "skip");
      }
    }

    for (const timer of dwellTimers.current) window.clearTimeout(timer);
    dwellTimers.current = [];
    activeSession.current = {
      campaignId: ad.campaign_id,
      variant: ad.variant_id,
      startedAt: performance.now(),
      earlySkipMs: (ad.duration_s ?? 10) * 250,
    };
    void emitSignal(ad.campaign_id, ad.variant_id, "impression");

    for (const threshold of dwellEventsFor(ad)) {
      const timer = window.setTimeout(() => {
        if (
          activeSession.current?.variant === ad.variant_id &&
          document.visibilityState === "visible"
        ) {
          void emitSignal(ad.campaign_id, ad.variant_id, threshold.event);
        }
      }, threshold.delay);
      dwellTimers.current.push(timer);
    }

    return () => {
      for (const timer of dwellTimers.current) window.clearTimeout(timer);
      dwellTimers.current = [];
    };
  }, [activeIndex, emitSignal]);

  const scrollTo = useCallback((index: number) => {
    const bounded = Math.max(0, Math.min(ads.length - 1, index));
    itemRefs.current[bounded]?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }, []);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (
        event.target instanceof HTMLElement &&
        event.target.closest("button, a, input, textarea, select")
      ) {
        return;
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        scrollTo(activeIndex + 1);
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        scrollTo(activeIndex - 1);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeIndex, scrollTo]);

  return (
    <main className="relative h-svh overflow-hidden bg-[#071311] text-white">
      <header className="pointer-events-none fixed inset-x-0 top-0 z-30 flex items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="pointer-events-auto flex items-center gap-2 rounded-full border border-white/15 bg-black/40 p-1.5 pr-4 shadow-xl backdrop-blur-xl">
          <Link
            href="/"
            className={buttonVariants({
              variant: "ghost",
              size: "icon",
              className:
                "rounded-full text-white hover:bg-white/15 hover:text-white",
            })}
            aria-label="Back to campaign dashboard"
          >
            <ArrowLeft />
          </Link>
          <div>
            <p className="text-xs font-semibold tracking-wide">AD LAB</p>
            <p className="text-[10px] text-white/55">
              {activeIndex + 1} / {ads.length}
            </p>
          </div>
        </div>

        <Button
          className="pointer-events-auto rounded-full border-white/15 bg-black/40 text-white shadow-xl backdrop-blur-xl hover:bg-white/15"
          variant="outline"
          onClick={() => void loadState()}
          disabled={stateLoading}
        >
          <RefreshCw
            className={stateLoading ? "animate-spin" : ""}
            aria-hidden="true"
          />
          <span className="hidden sm:inline">Refresh state</span>
        </Button>
      </header>

      <div
        className="h-full snap-y snap-mandatory overflow-y-auto overscroll-y-contain scroll-smooth"
        aria-label="Ad demo feed"
      >
        {ads.map((ad, index) => {
          const style = adStyles[index % adStyles.length];
          return (
            <section
              key={ad.id}
              ref={(element) => {
                itemRefs.current[index] = element;
              }}
              data-index={index}
              aria-label={`${style.brand} ad, ${index + 1} of ${ads.length}`}
              className="relative grid min-h-svh snap-start place-items-center gap-5 px-4 pb-10 pt-24 lg:grid-cols-[auto_minmax(22rem,27rem)] lg:gap-8 lg:px-10 lg:pb-8 lg:pt-20"
            >
              <div
                className="absolute inset-0 opacity-35"
                style={{
                  background: `radial-gradient(circle at 30% 30%, ${style.via}, transparent 36%), linear-gradient(145deg, ${style.from}, #071311 65%)`,
                }}
                aria-hidden="true"
              />

              <ScriptAdFrame
                ad={ad}
                active={index === activeIndex}
                style={style}
                onCta={() =>
                  void emitSignal(ad.campaign_id, ad.variant_id, "cta_tap")
                }
              />

              <StateCard
                ad={ad}
                campaign={campaign}
                loading={stateLoading}
                error={stateError}
                signalStatus={signalStatuses[ad.variant_id]}
                onRetry={loadState}
              />
            </section>
          );
        })}
      </div>

      <div className="pointer-events-none fixed bottom-4 right-4 z-30 hidden flex-col gap-2 lg:flex">
        <Button
          size="icon"
          variant="outline"
          className="pointer-events-auto rounded-full border-white/15 bg-black/40 text-white backdrop-blur-xl hover:bg-white/15"
          onClick={() => scrollTo(activeIndex - 1)}
          disabled={activeIndex === 0}
          aria-label="Previous ad"
        >
          <ArrowUp />
        </Button>
        <Button
          size="icon"
          variant="outline"
          className="pointer-events-auto rounded-full border-white/15 bg-black/40 text-white backdrop-blur-xl hover:bg-white/15"
          onClick={() => scrollTo(activeIndex + 1)}
          disabled={activeIndex === ads.length - 1}
          aria-label="Next ad"
        >
          <ArrowDown />
        </Button>
      </div>
    </main>
  );
}

function ScriptAdFrame({
  ad,
  active,
  style,
  onCta,
}: {
  ad: AdManifestItem;
  active: boolean;
  style: AdStyle;
  onCta: () => void;
}) {
  return (
    <article
      className="relative z-10 aspect-[9/16] h-[min(72svh,46rem)] max-w-[88vw] overflow-hidden rounded-[2rem] border border-white/20 shadow-2xl shadow-black/50"
      style={{
        background: `linear-gradient(165deg, ${style.from} 0%, ${style.via} 52%, ${style.to} 115%)`,
      }}
    >
      <div
        className={`absolute -right-16 top-[12%] size-56 rounded-full border-[28px] border-white/10 transition-transform duration-[2500ms] ${
          active ? "translate-x-0 rotate-12" : "translate-x-16 -rotate-12"
        }`}
        aria-hidden="true"
      />
      <div
        className={`absolute -left-20 bottom-[21%] h-48 w-72 rounded-[50%] bg-black/20 blur-sm transition-transform duration-[3500ms] ${
          active ? "translate-x-8 -rotate-6" : "-translate-x-10 rotate-6"
        }`}
        aria-hidden="true"
      />
      <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(0,0,0,.05),rgba(0,0,0,.08)_45%,rgba(0,0,0,.88))]" />

      <div className="absolute inset-x-0 top-0 flex items-center justify-between p-5">
        <Badge className="border-white/15 bg-black/25 text-white backdrop-blur-lg">
          {style.brand}
        </Badge>
        <span className="rounded-full border border-white/15 bg-black/20 px-3 py-1 text-[10px] font-semibold tracking-[0.18em] text-white/75 backdrop-blur-lg">
          SCRIPT PREVIEW
        </span>
      </div>

      <div className="absolute inset-x-0 top-[24%] px-7">
        <p className="text-[11px] font-semibold tracking-[0.2em] text-white/60 uppercase">
          The hook
        </p>
        <h1 className="mt-3 text-balance text-4xl font-semibold leading-[0.95] tracking-[-0.055em] drop-shadow-lg">
          {ad.hook}
        </h1>
      </div>

      <div className="absolute inset-x-0 bottom-0 p-5">
        <div className="mb-5 border-l-2 border-white/45 pl-3">
          <p className="line-clamp-2 text-sm leading-5 text-white/78">
            {ad.script ?? "Script preview"}
          </p>
        </div>
        <p className="mb-3 font-mono text-[10px] tracking-wide text-white/55">
          {ad.variant_id}
        </p>
        <Button
          size="lg"
          className="h-11 w-full rounded-full bg-white text-zinc-950 shadow-lg hover:bg-white/90"
          onClick={onCta}
        >
          {ad.cta}
          <ExternalLink aria-hidden="true" />
        </Button>
      </div>
    </article>
  );
}

function StateCard({
  ad,
  campaign,
  loading,
  error,
  signalStatus,
  onRetry,
}: {
  ad: AdManifestItem;
  campaign: CampaignState | null;
  loading: boolean;
  error: string | null;
  signalStatus?: SignalStatus;
  onRetry: () => Promise<void>;
}) {
  if (loading && !campaign) {
    return (
      <Card className="relative z-10 w-full max-w-md border-white/10 bg-black/35 text-white backdrop-blur-xl">
        <CardHeader>
          <CardTitle>Loading campaign state…</CardTitle>
          <CardDescription className="text-white/55">
            Reading compact counts for this variant.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-2">
          {Array.from({ length: 8 }).map((_, index) => (
            <div
              key={index}
              className="h-14 animate-pulse rounded-xl bg-white/8"
            />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error && !campaign) {
    return (
      <Card className="relative z-10 w-full max-w-md border-red-300/20 bg-red-950/35 text-white backdrop-blur-xl">
        <CardHeader>
          <CardTitle>State unavailable</CardTitle>
          <CardDescription className="text-red-100/70">
            {error}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" onClick={() => void onRetry()}>
            <RefreshCw aria-hidden="true" />
            Try again
          </Button>
        </CardContent>
      </Card>
    );
  }

  const counts: VariantCounts = campaign?.counts[ad.variant_id] ?? {};
  const hasFoldedState = campaign?.variants.includes(ad.variant_id) ?? false;
  const latestDecision = campaign?.decisions.at(-1);
  const decision = latestDecision
    ? latestDecision.winner_variant_id === ad.variant_id
      ? "Keep this variant"
      : `Keep ${latestDecision.winner_variant_id ?? "collecting data"}`
    : "No decision yet";
  const noiseFloor = campaign?.aa_noise_floor.absolute_rate_difference;

  const metrics: { label: string; value: number }[] = [
    { label: "Impressions", value: counts.impression ?? 0 },
    { label: "25%", value: counts.q25 ?? 0 },
    { label: "50%", value: counts.q50 ?? 0 },
    { label: "75%", value: counts.q75 ?? 0 },
    { label: "Complete", value: counts.complete ?? 0 },
    { label: "Skips", value: counts.skip ?? 0 },
    { label: "CTA taps", value: counts.cta_tap ?? 0 },
    { label: "Installs", value: counts.install ?? 0 },
  ];

  return (
    <Card className="relative z-10 w-full max-w-md border-white/10 bg-black/35 text-white shadow-2xl backdrop-blur-xl">
      <CardHeader className="border-b border-white/10">
        <div className="mb-2 flex items-center justify-between gap-3">
          <Badge
            className={
              hasFoldedState
                ? "bg-emerald-300 text-emerald-950"
                : "bg-white/10 text-white"
            }
          >
            {hasFoldedState ? (
              <>
                <Check aria-hidden="true" />
                Folded state
              </>
            ) : (
              "Awaiting first fold"
            )}
          </Badge>
          <span className="font-mono text-[10px] text-white/45">
            campaign/{ad.campaign_id}
          </span>
        </div>
        <CardTitle className="text-lg">Variant state</CardTitle>
        <CardDescription className="truncate font-mono text-xs text-white/55">
          {ad.variant_id}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-4 gap-2">
          {metrics.map((metric) => (
            <div
              key={metric.label}
              className="rounded-xl border border-white/8 bg-white/6 p-2.5"
            >
              <p className="font-mono text-lg font-semibold tabular-nums">
                {metric.value}
              </p>
              <p className="mt-0.5 text-[10px] text-white/50">{metric.label}</p>
            </div>
          ))}
        </div>

        <div className="mt-4 grid gap-2">
          <StateRow label="Current decision" value={decision} />
          <StateRow
            label="A/A noise floor"
            value={
              noiseFloor == null
                ? "Not estimated"
                : `${(noiseFloor * 100).toFixed(2)}%`
            }
          />
        </div>

        <div
          className="mt-4 flex min-h-9 items-center gap-2 rounded-xl border border-white/8 bg-black/20 px-3 text-xs text-white/60"
          aria-live="polite"
        >
          {signalStatus?.kind === "sending" ? (
            <RefreshCw className="size-3 animate-spin" aria-hidden="true" />
          ) : signalStatus?.kind === "accepted" ? (
            <Sparkles className="size-3 text-emerald-300" aria-hidden="true" />
          ) : null}
          <span
            className={
              signalStatus?.kind === "error" ? "text-red-200" : undefined
            }
          >
            {signalStatus?.message ??
              "Viewing emits one debounced impression and dwell milestones."}
          </span>
        </div>
        {!hasFoldedState ? (
          <p className="mt-3 text-[11px] leading-5 text-white/45">
            Accepted signals appear here after the campaign decision step folds
            the raw event window into compact state.
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

function StateRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-xl border border-white/8 px-3 py-2.5 text-xs">
      <span className="text-white/50">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  );
}
