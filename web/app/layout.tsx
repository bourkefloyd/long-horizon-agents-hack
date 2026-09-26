import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AudienceQr } from "@/components/audience-qr";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "LH Marketing",
    template: "%s · LH Marketing",
  },
  description:
    "Operate vertical video experiments and generate the next day's creative brief.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">
        {children}
        <AudienceQr />
      </body>
    </html>
  );
}
