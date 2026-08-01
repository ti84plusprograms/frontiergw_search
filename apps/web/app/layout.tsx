import "./globals.css";
import type { ReactNode } from "react";
import { Providers } from "./providers";

export const metadata = {
  title: "Frontier GoWild Destination Explorer",
  description: "Explore scheduled Frontier routes with estimated GoWild pricing",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>
        <Providers>
          <main id="main-content" className="mx-auto max-w-3xl px-4 py-6">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
