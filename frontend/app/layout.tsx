import type { Metadata, Viewport } from "next";

import { ThemeToggle } from "@/components/theme-toggle";

import "./globals.css";
import "./reference-ui.css";

export const metadata: Metadata = {
  title: {
    default: "ReceiptSplit — one receipt, cleanly shared",
    template: "%s | ReceiptSplit"
  },
  description:
    "Scan a receipt, let friends claim their items, see exact totals, and settle directly with the payer through UPI.",
  applicationName: "ReceiptSplit",
  keywords: ["receipt splitting", "bill splitting", "UPI", "item-wise split"],
  robots: {
    index: true,
    follow: true
  }
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1
};

const themeScript = `
(() => {
  try {
    const key = "receiptsplit:theme";
    const saved = localStorage.getItem(key);
    const theme = saved === "light" || saved === "dark"
      ? saved
      : (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.dataset.theme = theme;
  } catch {
    document.documentElement.classList.add("dark");
    document.documentElement.dataset.theme = "dark";
  }
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="theme-boot">
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        <ThemeToggle />
        {children}
      </body>
    </html>
  );
}
