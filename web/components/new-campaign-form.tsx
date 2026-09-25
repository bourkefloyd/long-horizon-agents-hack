"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ArrowRight, RefreshCw } from "lucide-react";

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
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  createCampaign,
  DIMS_OPTIONS,
  EXAMPLE_CAMPAIGN,
  VERTICAL_OPTIONS,
  type CampaignInput,
} from "@/lib/campaigns";

type FieldName = keyof CampaignInput;

const requiredMessage: Record<FieldName, string> = {
  name: "Give the campaign a name.",
  brief: "Describe what the creative should sell in a sentence or two.",
  vertical: "Pick a vertical.",
  geo: "Name the market, for example San Francisco.",
  audience: "Describe who should see this.",
  dims: "Pick an aspect ratio.",
};

export function NewCampaignForm() {
  const router = useRouter();
  const [values, setValues] = useState<CampaignInput>(EXAMPLE_CAMPAIGN);
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<FieldName, string>>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function update(field: FieldName, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
    if (fieldErrors[field]) {
      setFieldErrors((current) => ({ ...current, [field]: undefined }));
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    const missing = (Object.keys(requiredMessage) as FieldName[]).filter(
      (field) => values[field].trim() === "",
    );
    if (missing.length > 0) {
      setFieldErrors(
        Object.fromEntries(missing.map((field) => [field, requiredMessage[field]])),
      );
      return;
    }

    setSubmitting(true);
    try {
      const trimmed = Object.fromEntries(
        Object.entries(values).map(([key, value]) => [key, value.trim()]),
      ) as unknown as CampaignInput;
      const campaign = await createCampaign(trimmed);
      router.push(`/campaigns/${encodeURIComponent(campaign.id)}`);
    } catch (caught) {
      setSubmitError(
        caught instanceof Error ? caught.message : "The campaign was not saved.",
      );
      setSubmitting(false);
    }
  }

  return (
    <CampaignsPageShell
      crumbs={[{ label: "Campaigns", href: "/campaigns" }, { label: "New" }]}
      title="New campaign"
      description="Save the brief first. On the next screen you can queue it, which opens a labeled GitHub issue for the campaign-gen agent."
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(280px,0.8fr)]">
        <Card className="bg-card/90">
          <CardHeader>
            <CardTitle>Brief</CardTitle>
            <CardDescription>
              Prefilled with the SF Coffee Launch example. Edit anything and save.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} noValidate>
              <FieldGroup>
                <Field data-invalid={Boolean(fieldErrors.name)}>
                  <FieldLabel htmlFor="campaign-name">Name</FieldLabel>
                  <Input
                    id="campaign-name"
                    value={values.name}
                    onChange={(event) => update("name", event.target.value)}
                    placeholder="SF Coffee Launch"
                    maxLength={120}
                    aria-invalid={Boolean(fieldErrors.name)}
                    autoComplete="off"
                  />
                  <FieldDescription>
                    Becomes the campaign id (a slug) and the issue title.
                  </FieldDescription>
                  <FieldError>{fieldErrors.name}</FieldError>
                </Field>

                <Field data-invalid={Boolean(fieldErrors.brief)}>
                  <FieldLabel htmlFor="campaign-brief">Brief</FieldLabel>
                  <Textarea
                    id="campaign-brief"
                    value={values.brief}
                    onChange={(event) => update("brief", event.target.value)}
                    placeholder="Casual mobile game cross-promo for SF coffee lovers"
                    rows={4}
                    maxLength={4000}
                    aria-invalid={Boolean(fieldErrors.brief)}
                  />
                  <FieldDescription>
                    What the ad should sell and the tone. The agent pairs this with
                    fresh local stories from the market.
                  </FieldDescription>
                  <FieldError>{fieldErrors.brief}</FieldError>
                </Field>

                <div className="grid gap-5 sm:grid-cols-2">
                  <Field data-invalid={Boolean(fieldErrors.vertical)}>
                    <FieldLabel htmlFor="campaign-vertical">Vertical</FieldLabel>
                    <Select
                      value={values.vertical}
                      onValueChange={(value) => update("vertical", value ?? "")}
                    >
                      <SelectTrigger
                        id="campaign-vertical"
                        className="w-full"
                        aria-invalid={Boolean(fieldErrors.vertical)}
                      >
                        <SelectValue placeholder="Choose a vertical" />
                      </SelectTrigger>
                      <SelectContent>
                        {VERTICAL_OPTIONS.map((option) => (
                          <SelectItem key={option} value={option}>
                            {option}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FieldError>{fieldErrors.vertical}</FieldError>
                  </Field>

                  <Field data-invalid={Boolean(fieldErrors.geo)}>
                    <FieldLabel htmlFor="campaign-geo">Market</FieldLabel>
                    <Input
                      id="campaign-geo"
                      value={values.geo}
                      onChange={(event) => update("geo", event.target.value)}
                      placeholder="San Francisco"
                      maxLength={120}
                      aria-invalid={Boolean(fieldErrors.geo)}
                    />
                    <FieldDescription>Where local stories are sourced.</FieldDescription>
                    <FieldError>{fieldErrors.geo}</FieldError>
                  </Field>
                </div>

                <Field data-invalid={Boolean(fieldErrors.audience)}>
                  <FieldLabel htmlFor="campaign-audience">Audience</FieldLabel>
                  <Input
                    id="campaign-audience"
                    value={values.audience}
                    onChange={(event) => update("audience", event.target.value)}
                    placeholder="Coffee lovers, 21-40, commute by transit"
                    maxLength={240}
                    aria-invalid={Boolean(fieldErrors.audience)}
                  />
                  <FieldError>{fieldErrors.audience}</FieldError>
                </Field>

                <Field data-invalid={Boolean(fieldErrors.dims)} className="sm:max-w-56">
                  <FieldLabel htmlFor="campaign-dims">Aspect ratio</FieldLabel>
                  <Select
                    value={values.dims}
                    onValueChange={(value) => update("dims", value ?? "")}
                  >
                    <SelectTrigger id="campaign-dims" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {DIMS_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {option}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FieldDescription>9:16 matches the vertical feed.</FieldDescription>
                  <FieldError>{fieldErrors.dims}</FieldError>
                </Field>
              </FieldGroup>

              {submitError ? (
                <div
                  className="mt-6 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
                  role="alert"
                >
                  {submitError}
                </div>
              ) : null}

              <div className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                <Link
                  href="/campaigns"
                  className={buttonVariants({ variant: "outline", size: "lg" })}
                >
                  Cancel
                </Link>
                <Button
                  type="submit"
                  size="lg"
                  disabled={submitting}
                  className="bg-orange-600 text-white hover:bg-orange-700"
                >
                  {submitting ? (
                    <RefreshCw className="animate-spin" aria-hidden="true" />
                  ) : (
                    <ArrowRight aria-hidden="true" />
                  )}
                  {submitting ? "Saving…" : "Save campaign"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card className="h-fit bg-zinc-950 text-zinc-50">
          <CardHeader>
            <CardTitle>What happens next</CardTitle>
            <CardDescription className="text-zinc-400">
              Saving stores the campaign JSON. Queueing hands it to the agent.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ol className="space-y-4 text-sm leading-6 text-zinc-300">
              <li className="flex gap-3">
                <span className="font-mono text-orange-400">1</span>
                The service writes <code className="text-zinc-100">campaigns/&lt;id&gt;.json</code> to the ad asset bucket.
              </li>
              <li className="flex gap-3">
                <span className="font-mono text-orange-400">2</span>
                Generate opens a GitHub issue labeled{" "}
                <code className="text-zinc-100">lh:campaign-gen</code> with the brief and campaign JSON.
              </li>
              <li className="flex gap-3">
                <span className="font-mono text-orange-400">3</span>
                The campaign-gen agent researches the market and writes creative under{" "}
                <code className="text-zinc-100">cdn/staging/&lt;id&gt;/</code> for review.
              </li>
            </ol>
          </CardContent>
        </Card>
      </div>
    </CampaignsPageShell>
  );
}
