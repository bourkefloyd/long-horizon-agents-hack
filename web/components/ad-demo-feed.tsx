"use client";

import Link from "next/link";
import {
  ArrowLeft,
  Check,
  ExternalLink,
  RefreshCw,
  Sparkles,
  Volume2,
  VolumeX,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
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
import { GenerationStackPanel } from "@/components/generation-stack-panel";
import { localAdManifest } from "@/content/ads";
import {
  activeFeedAds,
  fetchAdManifest,
  type Ad,
} from "@/lib/ads";
import type { CampaignState, EventType, VariantCounts } from "@/lib/types";

const adStyles = [
  { brand: "Sightglass Coffee", from: "#071b2b", via: "#31515a", to: "#d5b887" },
  { brand: "Tartine Bakery", from: "#15354a", via: "#df8d55", to: "#f6d991" },
  { brand: "Bi-Rite Creamery", from: "#59284f", via: "#df5b78", to: "#ffcf8b" },
  { brand: "Dandelion Chocolate", from: "#21120d", via: "#75452d", to: "#d9ad74" },
  { brand: "Boudin Bakery", from: "#26343f", via: "#6e8791", to: "#e6b968" },
];
type AdStyle = (typeof adStyles)[number];

/**
 * Vertical creative fills the viewport below the feed chrome. The width is
 * the only sized axis: every ancestor up to the snap section has an auto
 * height, so a percentage (or `min(...)` containing one) on the block axis
 * resolves to `auto` and the frame collapses to its border. Deriving the
 * width from the viewport height keeps the box definite in every browser and
 * lets `aspect-ratio` produce the 9:16 height.
 */
const adFrameClass =
  "relative z-10 aspect-[9/16] w-[min(100%,calc((100svh-7.5rem)*9/16))] overflow-hidden border border-white/20 bg-black shadow-2xl shadow-black/50";
const adViewportClass = `${adFrameClass} rounded-[2rem]`;
/** Rendered video keeps hard edges so the creative is shown exactly as cut. */
const adVideoViewportClass = `${adFrameClass} rounded-none`;

const brandByPrefix: Record<string, AdStyle> = {
  sightglass: adStyles[0],
  tartine: adStyles[1],
  bi_rite: adStyles[2],
  dandelion: adStyles[3],
  boudin: adStyles[4],
};

/**
 * Known SF brands get their palette and name from the variant-id prefix;
 * anything else keeps a rotating palette but is labelled with its campaign
 * rather than a borrowed brand name.
 */
function brandForAd(ad: Ad, index: number, campaignLabel?: string): AdStyle {
  const prefix = ad.variant_id.split("__")[0] ?? "";
  const known = brandByPrefix[prefix];
  if (known) return known;
  return {
    ...adStyles[index % adStyles.length],
    brand: campaignLabel ?? ad.campaign_id,
  };
}

function localFallbackAds(): Ad[] {
  return activeFeedAds({
    version: 1,
    updated_at: new Date().toISOString(),
    ads: localAdManifest as Ad[],
  });
}

function dwellEventsFor(ad: Ad) {
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

async function getCampaignState(campaignId: string) {
  const response = await fetch(
    `/api/campaigns/${encodeURIComponent(campaignId)}/state`,
    { cache: "no-store" },
  );
  if (!response.ok) throw new Error(await responseMessage(response));
  return (await response.json()) as CampaignState;
}

async function getCampaignName(campaignId: string) {
  const response = await fetch(
    `/api/campaigns/${encodeURIComponent(campaignId)}`,
    { cache: "no-store" },
  );
  if (!response.ok) return null;
  const body = (await response.json()) as { name?: string };
  return body.name?.trim() || null;
}

export function AdDemoFeed({ campaignId }: { campaignId?: string }) {
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
  const [allAds, setAllAds] = useState<Ad[]>([]);
  const [manifestSource, setManifestSource] = useState<"cdn" | "local">(
    "local",
  );
  const [manifestLoading, setManifestLoading] = useState(true);
  const [manifestError, setManifestError] = useState<string | null>(null);
  const [campaignName, setCampaignName] = useState<string | null>(null);
  // Browsers only autoplay muted video; sound stays off until the viewer
  // opts in, then the choice follows them from ad to ad.
  const [soundOn, setSoundOn] = useState(false);

  // The manifest is loaded once; the campaign filter is applied on top so a
  // campaign with nothing published shows its own empty state instead of
  // falling back to the bundled demo ads.
  const ads = useMemo(
    () =>
      campaignId
        ? allAds.filter((ad) => ad.campaign_id === campaignId)
        : allAds,
    [allAds, campaignId],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadManifest() {
      setManifestLoading(true);
      setManifestError(null);
      try {
        const manifest = await fetchAdManifest();
        const active = activeFeedAds(manifest);
        if (active.length === 0) {
          throw new Error("CDN manifest returned zero active ads.");
        }
        if (!cancelled) {
          setAllAds(active);
          setManifestSource("cdn");
        }
      } catch (caught) {
        const fallback = localFallbackAds();
        if (!cancelled) {
          setAllAds(fallback);
          setManifestSource("local");
          setManifestError(
            caught instanceof Error
              ? caught.message
              : "Could not load the CDN manifest.",
          );
        }
      } finally {
        if (!cancelled) setManifestLoading(false);
      }
    }

    void loadManifest();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!campaignId) return;
    let cancelled = false;
    getCampaignName(campaignId)
      .then((name) => {
        if (!cancelled) setCampaignName(name);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [campaignId]);

  // The state card reads the campaign that owns the visible ad, so counts
  // line up with the variant on screen even when the feed mixes campaigns.
  const stateCampaignId =
    campaignId ?? ads[activeIndex]?.campaign_id ?? ads[0]?.campaign_id ?? "demo";

  const loadState = useCallback(async () => {
    setStateLoading(true);
    setStateError(null);
    try {
      setCampaign(await getCampaignState(stateCampaignId));
    } catch (caught) {
      setStateError(
        caught instanceof Error
          ? caught.message
          : "Campaign state is unavailable.",
      );
    } finally {
      setStateLoading(false);
    }
  }, [stateCampaignId]);

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
    if (ads.length === 0) return;

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
  }, [activeIndex, ads.length]);

  useEffect(() => {
    const ad = ads[activeIndex];
    if (!ad) return;
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
  }, [activeIndex, ads, emitSignal]);

  const scrollTo = useCallback(
    (index: number) => {
      const bounded = Math.max(0, Math.min(ads.length - 1, index));
      itemRefs.current[bounded]?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    },
    [ads.length],
  );

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

  if (manifestLoading) {
    return (
      <main className="grid h-svh place-items-center bg-[#071311] text-white">
        <p className="text-sm text-white/70">Loading ad manifest…</p>
      </main>
    );
  }

  if (ads.length === 0 && campaignId) {
    const campaignHref = `/campaigns/${encodeURIComponent(campaignId)}`;
    return (
      <main className="grid h-svh place-items-center bg-[#071311] px-6 text-center text-white">
        <div className="flex max-w-sm flex-col items-center gap-4">
          <p className="text-[10px] font-semibold tracking-[0.22em] text-white/45 uppercase">
            {campaignName ?? campaignId}
          </p>
          <h1 className="text-xl font-semibold tracking-tight">
            No ads published yet for this campaign
          </h1>
          <p className="text-sm leading-6 text-white/60">
            Creative appears here once the campaign&apos;s variants are staged
            and published to the CDN manifest.
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            <Link
              href={campaignHref}
              className={buttonVariants({
                size: "lg",
                className:
                  "rounded-full bg-white text-zinc-950 hover:bg-white/90",
              })}
            >
              <ArrowLeft aria-hidden="true" />
              Back to campaign
            </Link>
            <Link
              href="/feed"
              className={buttonVariants({
                size: "lg",
                variant: "outline",
                className:
                  "rounded-full border-white/15 bg-transparent text-white hover:bg-white/10 hover:text-white",
              })}
            >
              All ads
            </Link>
          </div>
        </div>
      </main>
    );
  }

  if (ads.length === 0) {
    return (
      <main className="grid h-svh place-items-center bg-[#071311] px-6 text-center text-white">
        <p className="text-sm text-white/70">
          {manifestError ?? "No active ads are available."}
        </p>
      </main>
    );
  }

  const activeAd = ads[activeIndex];

  return (
    <main className="grid h-svh grid-cols-1 grid-rows-[minmax(0,1fr)] bg-[#071311] text-white lg:grid-cols-[minmax(0,1fr)_min(26rem,34vw)]">
      <div className="relative min-h-0 overflow-hidden">
      <header className="pointer-events-none absolute inset-x-0 top-0 z-30 flex items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="pointer-events-auto flex items-center gap-2 rounded-full border border-white/15 bg-black/40 p-1.5 pr-4 shadow-xl backdrop-blur-xl">
          <Link
            href={
              campaignId
                ? `/campaigns/${encodeURIComponent(campaignId)}`
                : "/"
            }
            className={buttonVariants({
              variant: "ghost",
              size: "icon",
              className:
                "rounded-full text-white hover:bg-white/15 hover:text-white",
            })}
            aria-label={
              campaignId ? "Back to campaign" : "Back to campaign dashboard"
            }
          >
            <ArrowLeft />
          </Link>
          <div>
            <p className="text-xs font-semibold tracking-wide">AD LAB</p>
            <p className="max-w-40 truncate text-[10px] text-white/55">
              {activeIndex + 1} / {ads.length}
              {campaignId ? ` · ${campaignName ?? campaignId}` : ""}
            </p>
          </div>
          <Badge
            className={
              manifestSource === "cdn"
                ? "border-emerald-300/30 bg-emerald-400/15 text-emerald-100"
                : "border-amber-300/30 bg-amber-400/15 text-amber-100"
            }
            title={
              manifestError ??
              (manifestSource === "cdn"
                ? "Loaded from the public CDN manifest"
                : "Using bundled local manifest")
            }
          >
            {manifestSource === "cdn" ? "CDN" : "Local"}
          </Badge>
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
        // Mandatory snapping only on the split layout: on a phone each section
        // is taller than the screen (frame + info card), and iOS snaps a tall
        // section back to its start, trapping the content below the fold.
        className="h-full overflow-y-auto scroll-smooth pt-[4.25rem] scroll-pt-[4.25rem] lg:snap-y lg:snap-mandatory lg:overscroll-y-contain"
        aria-label="Ad experience"
      >
        {ads.map((ad, index) => {
          const style = brandForAd(
            ad,
            index,
            campaignId === ad.campaign_id ? campaignName ?? undefined : undefined,
          );
          const isActive = index === activeIndex;
          return (
            <section
              key={ad.id}
              ref={(element) => {
                itemRefs.current[index] = element;
              }}
              data-index={index}
              aria-label={`${style.brand} ad, ${index + 1} of ${ads.length}`}
              className="relative flex min-h-[calc(100svh-4.25rem)] snap-start flex-col lg:min-h-[calc(100svh-4.25rem)]"
            >
              <div
                className="pointer-events-none absolute inset-0 opacity-35"
                style={{
                  background: `radial-gradient(circle at 30% 30%, ${style.via}, transparent 36%), linear-gradient(145deg, ${style.from}, #071311 65%)`,
                }}
                aria-hidden="true"
              />

              <div className="relative z-10 flex flex-1 flex-col">
                <div className="flex flex-1 items-center justify-center px-4 py-3 lg:px-8">
                  <div className="flex w-full max-w-xl flex-col items-center gap-2">
                    <ColumnHeading
                      title="Ad experience"
                      detail={
                        campaignId
                          ? `${campaignName ?? campaignId} · 9:16`
                          : "What the viewer sees · 9:16"
                      }
                      className="w-[min(100%,calc((100svh-7.5rem)*9/16))]"
                    />
                    <AdCreativeFrame
                      ad={ad}
                      active={isActive}
                      style={style}
                      shellClassName={
                        ad.media_type === "video"
                          ? adVideoViewportClass
                          : adViewportClass
                      }
                      soundOn={soundOn}
                      onSoundChange={setSoundOn}
                      onCta={() =>
                        void emitSignal(
                          ad.campaign_id,
                          ad.variant_id,
                          "cta_tap",
                        )
                      }
                    />
                  </div>
                </div>

                <div className="space-y-4 px-4 pb-8 lg:hidden">
                  <ColumnHeading
                    title="Info card"
                    detail="What the system knows"
                  />
                  <StateCard
                    ad={ad}
                    campaign={campaign}
                    loading={stateLoading}
                    error={stateError}
                    signalStatus={signalStatuses[ad.variant_id]}
                    onRetry={loadState}
                  />
                  {isActive ? (
                    <GenerationStackPanel
                      ad={ad}
                      onBriefReady={() => void loadState()}
                    />
                  ) : null}
                </div>
              </div>
            </section>
          );
        })}
      </div>

      <nav
        className="absolute right-2 top-1/2 z-30 flex -translate-y-1/2 flex-col items-center gap-1 rounded-full bg-black/25 px-1.5 py-2 backdrop-blur-md sm:right-3"
        aria-label="Ad position"
      >
        {ads.map((ad, index) => {
          const isCurrent = index === activeIndex;
          return (
            <button
              key={ad.id}
              type="button"
              className="group grid size-4 place-items-center"
              onClick={() => scrollTo(index)}
              aria-label={`Go to ad ${index + 1} of ${ads.length}`}
              aria-current={isCurrent ? "true" : undefined}
            >
              <span
                className={`block rounded-full transition-all duration-300 ${
                  isCurrent
                    ? "size-2 bg-white shadow-[0_0_6px_rgba(255,255,255,.6)]"
                    : "size-1.5 bg-white/35 group-hover:bg-white/70"
                }`}
              />
            </button>
          );
        })}
      </nav>
      </div>

      {/* Block flow, not a flex column: a fixed-height flex column shrinks and
          clips its cards instead of letting the panel scroll. */}
      <aside
        className="hidden min-h-0 overflow-y-auto overscroll-y-contain border-l border-white/10 bg-[#050b0a]/90 p-4 lg:block"
        aria-label="Info card"
      >
        <div className="flex flex-col gap-4">
          <div>
            <p className="text-[10px] font-semibold tracking-[0.22em] text-white/45 uppercase">
              Info card
            </p>
            <h2 className="mt-1 text-lg font-semibold tracking-tight">
              What the system knows
            </h2>
            <p className="mt-1 text-xs leading-5 text-white/50">
              Targeting, tracked signals and the tools behind the visible ad.
            </p>
          </div>
          {activeAd ? (
            <>
              <StateCard
                ad={activeAd}
                campaign={campaign}
                loading={stateLoading}
                error={stateError}
                signalStatus={signalStatuses[activeAd.variant_id]}
                onRetry={loadState}
              />
              <GenerationStackPanel
                ad={activeAd}
                onBriefReady={() => void loadState()}
              />
            </>
          ) : null}
        </div>
      </aside>
    </main>
  );
}

function AdCreativeFrame({
  ad,
  active,
  style,
  shellClassName,
  soundOn,
  onSoundChange,
  onCta,
}: {
  ad: Ad;
  active: boolean;
  style: AdStyle;
  shellClassName: string;
  soundOn: boolean;
  onSoundChange: (soundOn: boolean) => void;
  onCta: () => void;
}) {
  switch (ad.media_type) {
    case "image":
      return (
        <ImageAdFrame
          ad={ad}
          active={active}
          style={style}
          shellClassName={shellClassName}
          onCta={onCta}
        />
      );
    case "video":
      return (
        <VideoAdFrame
          ad={ad}
          active={active}
          style={style}
          shellClassName={shellClassName}
          soundOn={soundOn}
          onSoundChange={onSoundChange}
          onCta={onCta}
        />
      );
    case "script":
    default:
      return (
        <ScriptAdFrame
          ad={ad}
          active={active}
          style={style}
          shellClassName={shellClassName}
          onCta={onCta}
        />
      );
  }
}

function ImageAdFrame({
  ad,
  active,
  style,
  shellClassName,
  onCta,
}: {
  ad: Ad;
  active: boolean;
  style: AdStyle;
  shellClassName: string;
  onCta: () => void;
}) {
  const imageUrl = ad.poster_url ?? ad.media_url;
  return (
    <article className={shellClassName}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={imageUrl}
        alt=""
        className={`absolute inset-0 h-full w-full object-cover transition-transform duration-[2500ms] ${
          active ? "scale-100" : "scale-105"
        }`}
      />
      <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(0,0,0,.08),rgba(0,0,0,.88))]" />

      <div className="absolute inset-x-0 top-0 flex items-center justify-between p-5">
        <Badge className="border-white/15 bg-black/25 text-white backdrop-blur-lg">
          {style.brand}
        </Badge>
        <span className="rounded-full border border-white/15 bg-black/20 px-3 py-1 text-[10px] font-semibold tracking-[0.18em] text-white/75 backdrop-blur-lg">
          POSTER
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

function VideoAdFrame({
  ad,
  active,
  style,
  shellClassName,
  soundOn,
  onSoundChange,
  onCta,
}: {
  ad: Ad;
  active: boolean;
  style: AdStyle;
  shellClassName: string;
  soundOn: boolean;
  onSoundChange: (soundOn: boolean) => void;
  onCta: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [failedMediaUrl, setFailedMediaUrl] = useState<string | null>(null);
  const videoFailed = failedMediaUrl === ad.media_url;

  // `autoPlay` only applies when the element first loads, so drive playback
  // from the active flag: play the visible ad, pause and rewind the others.
  // A rejected play() is not a media failure: the paused element keeps
  // showing its poster. If the browser refuses unmuted playback (no gesture
  // on this page yet), fall back to muted and report sound as off.
  useEffect(() => {
    const video = videoRef.current;
    if (!video || videoFailed) return;
    if (!active) {
      video.pause();
      video.currentTime = 0;
      return;
    }
    video.muted = !soundOn;
    video.play()?.catch(() => {
      if (!soundOn) return;
      video.muted = true;
      onSoundChange(false);
      video.play()?.catch(() => undefined);
    });
  }, [active, soundOn, videoFailed, onSoundChange]);

  function toggleSound() {
    const next = !soundOn;
    const video = videoRef.current;
    // Flip the element inside the click handler so the gesture covers it.
    if (video) {
      video.muted = !next;
      if (next && video.paused) video.play()?.catch(() => undefined);
    }
    onSoundChange(next);
  }

  return (
    <article className={shellClassName}>
      {videoFailed && ad.poster_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={ad.poster_url}
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
      ) : (
        <video
          ref={videoRef}
          className="absolute inset-0 h-full w-full object-cover"
          src={ad.media_url}
          poster={ad.poster_url}
          playsInline
          muted={!soundOn}
          loop
          autoPlay={active}
          preload="metadata"
          controls={false}
          onError={() => setFailedMediaUrl(ad.media_url)}
        />
      )}
      <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(0,0,0,.05),rgba(0,0,0,.88))]" />

      <div className="absolute inset-x-0 top-0 flex items-center justify-between p-5">
        <Badge className="border-white/15 bg-black/25 text-white backdrop-blur-lg">
          {style.brand}
        </Badge>
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-white/15 bg-black/20 px-3 py-1 text-[10px] font-semibold tracking-[0.18em] text-white/75 backdrop-blur-lg">
            VIDEO
          </span>
          {!videoFailed ? (
            <Button
              size="icon"
              variant="outline"
              className="size-8 rounded-full border-white/15 bg-black/25 text-white backdrop-blur-lg hover:bg-white/15 hover:text-white"
              onClick={toggleSound}
              aria-pressed={soundOn}
              aria-label={soundOn ? "Mute video" : "Unmute video"}
            >
              {soundOn ? (
                <Volume2 className="size-4" aria-hidden="true" />
              ) : (
                <VolumeX className="size-4" aria-hidden="true" />
              )}
            </Button>
          ) : null}
        </div>
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

function ScriptAdFrame({
  ad,
  active,
  style,
  shellClassName,
  onCta,
}: {
  ad: Ad;
  active: boolean;
  style: AdStyle;
  shellClassName: string;
  onCta: () => void;
}) {
  return (
    <article
      className={shellClassName}
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
  ad: Ad;
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
        <div className="mb-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
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
          <span className="min-w-0 max-w-full truncate font-mono text-[10px] text-white/45">
            campaign/{ad.campaign_id}
          </span>
        </div>
        <CardTitle className="text-lg">Variant state</CardTitle>
        <CardDescription className="text-xs leading-5 text-white/55">
          Targeting fields and interaction counts for{" "}
          <span className="font-mono text-white/70">{ad.variant_id}</span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="mb-4 grid gap-2 rounded-xl border border-white/8 bg-black/20 p-3 text-xs">
          <StateRow
            label="Audience"
            value={
              Array.isArray(ad.targeting.audience)
                ? ad.targeting.audience.join(", ") || "Open"
                : ad.targeting.audience ?? "Open"
            }
          />
          <StateRow
            label="Geo"
            value={
              Array.isArray(ad.targeting.geo)
                ? ad.targeting.geo.join(", ") || "Open"
                : ad.targeting.geo ?? "Open"
            }
          />
          <StateRow
            label="Weight"
            value={String(ad.targeting.weight)}
          />
        </div>
        <div className="grid grid-cols-4 gap-2" data-metrics="">
          {metrics.map((metric) => (
            <div
              key={metric.label}
              className="min-w-0 rounded-xl border border-white/8 bg-white/6 p-2.5"
            >
              <p className="font-mono text-lg font-semibold tabular-nums">
                {metric.value}
              </p>
              <p className="mt-0.5 truncate text-[10px] text-white/50">
                {metric.label}
              </p>
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

function ColumnHeading({
  title,
  detail,
  className = "",
}: {
  title: string;
  detail: string;
  className?: string;
}) {
  return (
    <div
      className={`flex items-baseline justify-between gap-3 text-[10px] font-semibold tracking-[0.22em] uppercase ${className}`}
    >
      <span className="text-white/70">{title}</span>
      <span className="truncate text-right tracking-[0.12em] text-white/40">
        {detail}
      </span>
    </div>
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
