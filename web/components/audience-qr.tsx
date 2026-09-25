"use client";

import { QrCode } from "lucide-react";
import { usePathname } from "next/navigation";
import { toDataURL } from "qrcode";
import { useEffect, useState, useSyncExternalStore } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { cn } from "cn";

const QR_PX = 320;

function configuredOrigin() {
  const configured = process.env.NEXT_PUBLIC_SITE_URL?.trim();
  return configured ? configured.replace(/\/$/, "") : "";
}

function subscribeToOrigin() {
  return () => {};
}

function readOrigin() {
  return configuredOrigin() || window.location.origin;
}

function campaignCreateUrl(origin: string) {
  return `${origin}/campaigns/new`;
}

export function AudienceQr() {
  const pathname = usePathname();
  const onFeed = pathname === "/feed" || pathname.startsWith("/feed/");
  const origin = useSyncExternalStore(
    subscribeToOrigin,
    readOrigin,
    configuredOrigin,
  );
  const url = origin ? campaignCreateUrl(origin) : null;
  const [qrSrc, setQrSrc] = useState<string | null>(null);

  useEffect(() => {
    if (!url) return;
    let cancelled = false;
    toDataURL(url, {
      width: QR_PX,
      margin: 2,
      errorCorrectionLevel: "M",
      color: { dark: "#000000ff", light: "#ffffffff" },
    })
      .then((dataUrl) => {
        if (!cancelled) setQrSrc(dataUrl);
      })
      .catch(() => {
        if (!cancelled) setQrSrc(null);
      });
    return () => {
      cancelled = true;
    };
  }, [url]);

  return (
    <header className="pointer-events-none fixed inset-x-0 top-0 z-40">
      <Dialog>
        <DialogTrigger
          data-audience-qr
          aria-label="Show QR code to create your own campaign"
          className={cn(
            "pointer-events-auto absolute top-2.5 z-40 flex size-9 flex-col items-center justify-center gap-px rounded-md border border-black/20 bg-white text-black shadow-md outline-none hover:bg-neutral-100 focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2",
            // Feed header actions and the vertical dot rail own the right edge.
            // Keep this 36px chip in the top band, left of those controls.
            onFeed ? "right-16 sm:right-48" : "right-2.5",
          )}
        >
          <QrCode className="size-3.5" aria-hidden="true" />
          <span className="text-[9px] font-semibold leading-none tracking-wide">
            QR
          </span>
        </DialogTrigger>
        <DialogContent className="w-auto border border-black/10 bg-white text-black shadow-2xl ring-black/10 sm:max-w-md">
          <DialogHeader className="pr-8">
            <DialogTitle className="text-center text-base text-black">
              Scan to create your own campaign
            </DialogTitle>
          </DialogHeader>
          <div className="mx-auto bg-white p-2">
            {qrSrc ? (
              // Data-URL QR from the qrcode package; next/image does not add value here.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={qrSrc}
                width={QR_PX}
                height={QR_PX}
                alt={url ? `QR code for ${url}` : "QR code"}
                className="size-80 bg-white"
              />
            ) : (
              <div className="grid size-80 place-items-center bg-white text-sm text-neutral-700">
                {url ? "QR code unavailable" : "Preparing QR code"}
              </div>
            )}
          </div>
          <DialogDescription className="break-all text-center font-mono text-xs text-black">
            {url ?? "Preparing link"}
          </DialogDescription>
        </DialogContent>
      </Dialog>
    </header>
  );
}
