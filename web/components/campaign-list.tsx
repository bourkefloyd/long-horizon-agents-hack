"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ExternalLink, Megaphone, Plus, RefreshCw } from "lucide-react";

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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatCreatedAt, listCampaigns, type Campaign } from "@/lib/campaigns";

export function CampaignList() {
  const [campaigns, setCampaigns] = useState<Campaign[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setCampaigns(await listCampaigns());
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The campaign list is unavailable.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    listCampaigns()
      .then((records) => {
        if (!cancelled) setCampaigns(records);
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(
            caught instanceof Error
              ? caught.message
              : "The campaign list is unavailable.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <CampaignsPageShell
      crumbs={[{ label: "Campaigns" }]}
      title="Campaigns"
      description="Each campaign is a brief the campaign-gen agent turns into local, brand-safe vertical creative. Create one, then queue it to open the agent's task issue."
      actions={
        <>
          <Button
            variant="outline"
            size="lg"
            onClick={() => void load()}
            disabled={loading}
          >
            <RefreshCw
              className={loading ? "animate-spin" : undefined}
              aria-hidden="true"
            />
            Refresh
          </Button>
          <Link
            href="/campaigns/new"
            className={buttonVariants({ size: "lg" }) + " bg-orange-600 text-white hover:bg-orange-700"}
          >
            <Plus aria-hidden="true" />
            New campaign
          </Link>
        </>
      }
    >
      {loading && campaigns === null ? (
        <div
          className="flex min-h-48 items-center justify-center gap-3 text-sm font-medium text-muted-foreground"
          role="status"
        >
          <RefreshCw className="size-4 animate-spin" aria-hidden="true" />
          Loading campaigns…
        </div>
      ) : error && campaigns === null ? (
        <Card className="border-destructive/30 bg-card/90">
          <CardHeader>
            <CardTitle>Campaigns could not be loaded</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => void load()}>
              <RefreshCw aria-hidden="true" />
              Try again
            </Button>
          </CardContent>
        </Card>
      ) : campaigns && campaigns.length === 0 ? (
        <EmptyCampaigns />
      ) : (
        <>
          {error ? (
            <div
              className="mb-4 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
              role="alert"
            >
              {error}
            </div>
          ) : null}
          <Card className="overflow-hidden bg-card/90">
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="min-w-56 pl-6">Campaign</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="hidden md:table-cell">
                        Market
                      </TableHead>
                      <TableHead className="hidden lg:table-cell">
                        Vertical
                      </TableHead>
                      <TableHead className="hidden sm:table-cell">
                        Created
                      </TableHead>
                      <TableHead className="pr-6 text-right">Task</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {campaigns?.map((campaign) => (
                      <TableRow key={campaign.id}>
                        <TableCell className="pl-6">
                          <Link
                            href={`/campaigns/${encodeURIComponent(campaign.id)}`}
                            className="font-medium hover:underline"
                          >
                            {campaign.name}
                          </Link>
                          <p className="mt-0.5 font-mono text-xs text-muted-foreground">
                            {campaign.id} · {campaign.dims}
                          </p>
                        </TableCell>
                        <TableCell>
                          <CampaignStatusBadge status={campaign.status} />
                        </TableCell>
                        <TableCell className="hidden md:table-cell">
                          {campaign.geo}
                        </TableCell>
                        <TableCell className="hidden lg:table-cell">
                          {campaign.vertical}
                        </TableCell>
                        <TableCell className="hidden font-mono text-xs text-muted-foreground sm:table-cell">
                          {formatCreatedAt(campaign.created_at)}
                        </TableCell>
                        <TableCell className="pr-6 text-right">
                          {campaign.issue_url ? (
                            <a
                              href={campaign.issue_url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 text-sm font-medium text-orange-700 hover:underline"
                            >
                              Issue
                              <ExternalLink className="size-3.5" aria-hidden="true" />
                            </a>
                          ) : (
                            <span className="text-sm text-muted-foreground">
                              Not queued
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </CampaignsPageShell>
  );
}

function EmptyCampaigns() {
  return (
    <Card className="bg-card/90">
      <CardContent className="flex min-h-72 flex-col items-center justify-center px-6 text-center">
        <div className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-muted">
          <Megaphone className="size-5 text-muted-foreground" aria-hidden="true" />
        </div>
        <h2 className="font-semibold">No campaigns yet</h2>
        <p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
          Start with a name, a one-line brief, and a market. The form is prefilled
          with the SF Coffee Launch example so you can queue a run right away.
        </p>
        <Link
          href="/campaigns/new"
          className={buttonVariants({ size: "lg" }) + " mt-6 bg-orange-600 text-white hover:bg-orange-700"}
        >
          <Plus aria-hidden="true" />
          Create the first campaign
        </Link>
      </CardContent>
    </Card>
  );
}
