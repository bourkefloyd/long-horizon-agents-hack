"use client";

import { useEffect, useState, type ReactNode } from "react";
import {
  Database,
  LoaderCircle,
  Radio,
  Sparkles,
  Video,
  Wand2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Ad } from "@/lib/ads";
import type { GenerationStatus } from "@/lib/generation-env";

type NimbleStory = {
  title: string;
  url: string;
  source: string;
  snippet: string;
};

export function GenerationStackPanel({
  ad,
  onBriefReady,
}: {
  ad: Ad;
  onBriefReady?: () => void;
}) {
  const [status, setStatus] = useState<GenerationStatus | null>(null);
  const [nimbleStories, setNimbleStories] = useState<NimbleStory[]>([]);
  const [nimbleMode, setNimbleMode] = useState<string | null>(null);
  const [bflPreview, setBflPreview] = useState<string | null>(null);
  const [liquidMessage, setLiquidMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState<
    "nimble" | "bfl" | "liquid" | "status" | null
  >(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/generation/status", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("Could not read generation status.");
        return response.json() as Promise<GenerationStatus>;
      })
      .then((data) => {
        if (!cancelled) setStatus(data);
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Generation status failed.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function runNimble() {
    setBusy("nimble");
    setError(null);
    try {
      const response = await fetch("/api/generation/nimble", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          market: "San Francisco",
          limit: 3,
          use_mock: !status?.nimble.configured,
        }),
      });
      if (!response.ok) {
        const body = (await response.json()) as { detail?: string };
        throw new Error(body.detail ?? "Nimble discover failed.");
      }
      const body = (await response.json()) as {
        mode: string;
        stories: NimbleStory[];
      };
      setNimbleMode(body.mode);
      setNimbleStories(body.stories);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Nimble discover failed.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function previewBfl(generate = false) {
    setBusy("bfl");
    setError(null);
    try {
      const response = await fetch("/api/generation/bfl", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          hook: ad.hook,
          script: ad.script,
          generate,
        }),
      });
      if (!response.ok) {
        const body = (await response.json()) as { detail?: string };
        throw new Error(body.detail ?? "BFL request failed.");
      }
      const body = (await response.json()) as {
        mode: string;
        payload?: { prompt?: string };
        result?: unknown;
      };
      if (body.mode === "submitted") {
        setBflPreview("Render job submitted to FLUX 3 video.");
      } else {
        setBflPreview(
          body.payload?.prompt?.slice(0, 160) ??
            "Preview ready for FLUX 3 video.",
        );
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "BFL request failed.");
    } finally {
      setBusy(null);
    }
  }

  async function runLiquidFold() {
    setBusy("liquid");
    setError(null);
    setLiquidMessage(null);
    try {
      const response = await fetch("/api/generation/liquid/decide", {
        method: "POST",
      });
      if (!response.ok) {
        const body = (await response.json()) as { detail?: string };
        throw new Error(body.detail ?? "Liquid fold failed.");
      }
      const body = (await response.json()) as {
        next_day_brief?: { instruction?: string };
      };
      setLiquidMessage(
        body.next_day_brief?.instruction ??
          "Fold complete. Campaign state updated.",
      );
      onBriefReady?.();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Liquid fold failed.",
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card className="border-white/10 bg-black/35 text-white backdrop-blur-xl">
      <CardHeader className="border-b border-white/10 pb-4">
        <CardTitle className="text-base">Generation stack</CardTitle>
        <CardDescription className="text-white/55">
          The tools behind this ad and what each one does.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 pt-4">
        {error ? (
          <p className="rounded-lg border border-red-400/30 bg-red-950/40 px-3 py-2 text-xs text-red-100">
            {error}
          </p>
        ) : null}

        <StackRow
          icon={<Radio className="size-4" aria-hidden="true" />}
          title="Nimble"
          subtitle="Local data for generation: SF news and hooks"
          ready={status?.nimble.configured}
          readyLabel={status?.nimble.configured ? "Live key" : "Mock mode"}
          actionLabel={busy === "nimble" ? "Discovering…" : "Discover news"}
          disabled={busy !== null}
          onAction={() => void runNimble()}
        />
        {nimbleStories.length > 0 ? (
          <ul className="space-y-2 rounded-xl border border-white/8 bg-black/25 p-3 text-xs text-white/70">
            <li className="font-mono text-[10px] uppercase tracking-wide text-white/45">
              {nimbleMode ?? "mock"} · top {nimbleStories.length}
            </li>
            {nimbleStories.map((story) => (
              <li key={story.url}>
                <p className="font-medium text-white/90">{story.title}</p>
                <p className="line-clamp-2">{story.snippet}</p>
              </li>
            ))}
          </ul>
        ) : null}

        <StackRow
          icon={<Video className="size-4" aria-hidden="true" />}
          title="BFL (Black Forest Labs)"
          subtitle="Content generation: posters and video"
          ready={status?.bfl.configured}
          readyLabel={status?.bfl.configured ? "API key" : "Preview only"}
          actionLabel={busy === "bfl" ? "Working…" : "Preview prompt"}
          disabled={busy !== null}
          onAction={() => void previewBfl(false)}
        />
        {bflPreview ? (
          <p className="rounded-xl border border-white/8 bg-white/5 px-3 py-2 text-xs leading-5 text-white/65">
            {bflPreview}
          </p>
        ) : null}
        {status?.bfl.configured ? (
          <Button
            size="sm"
            variant="outline"
            className="border-white/15 bg-transparent text-white hover:bg-white/10"
            disabled={busy !== null}
            onClick={() => void previewBfl(true)}
          >
            {busy === "bfl" ? (
              <LoaderCircle className="animate-spin" aria-hidden="true" />
            ) : (
              <Wand2 aria-hidden="true" />
            )}
            Submit FLUX 3 job
          </Button>
        ) : null}

        <StackRow
          icon={<Database className="size-4" aria-hidden="true" />}
          title="Tinybird"
          subtitle="Memory: signal history (TBD, not wired)"
          ready={false}
          readyLabel="Not wired"
        />

        <StackRow
          icon={<Sparkles className="size-4" aria-hidden="true" />}
          title="Liquid fold"
          subtitle="Decision: fold signals into the next-day brief"
          ready={status?.liquid.configured}
          readyLabel={status?.liquid.configured ? "Campaign API" : "Offline"}
          actionLabel={busy === "liquid" ? "Folding…" : "Run decide step"}
          disabled={busy !== null || !status?.liquid.configured}
          onAction={() => void runLiquidFold()}
        />
        {liquidMessage ? (
          <p className="rounded-xl border border-emerald-400/20 bg-emerald-950/30 px-3 py-2 text-xs leading-5 text-emerald-100">
            {liquidMessage}
          </p>
        ) : null}

        <p className="text-[10px] leading-5 text-white/40">
          Source agent:{" "}
          <span className="font-mono text-white/55">{ad.source.agent}</span>
        </p>
      </CardContent>
    </Card>
  );
}

function StackRow({
  icon,
  title,
  subtitle,
  ready,
  readyLabel,
  actionLabel,
  disabled,
  onAction,
}: {
  icon: ReactNode;
  title: string;
  subtitle: string;
  ready?: boolean;
  readyLabel?: string;
  actionLabel?: string;
  disabled?: boolean;
  onAction?: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-white/8 bg-white/5 p-3">
      <div className="flex gap-3">
        <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-white/10">
          {icon}
        </div>
        <div>
          <p className="text-sm font-medium">{title}</p>
          <p className="text-xs text-white/55">{subtitle}</p>
          <Badge
            className={
              ready
                ? "mt-2 border-emerald-300/30 bg-emerald-400/15 text-emerald-100"
                : "mt-2 border-white/15 bg-white/10 text-white/70"
            }
          >
            {readyLabel ?? "Unknown"}
          </Badge>
        </div>
      </div>
      {actionLabel && onAction ? (
        <Button
          size="sm"
          variant="outline"
          className="shrink-0 border-white/15 bg-black/30 text-white hover:bg-white/10"
          disabled={disabled}
          onClick={onAction}
        >
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}
