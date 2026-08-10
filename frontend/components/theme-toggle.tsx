"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

const THEME_KEY = "receiptsplit:theme";
type Theme = "light" | "dark";

function getPreferredTheme(): Theme {
  if (typeof window === "undefined") {
    return "dark";
  }
  const saved = window.localStorage.getItem(THEME_KEY);
  if (saved === "light" || saved === "dark") {
    return saved;
  }
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.documentElement.dataset.theme = theme;
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      const preferred = getPreferredTheme();
      setTheme(preferred);
      applyTheme(preferred);
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  function toggleTheme() {
    const activeTheme = theme ?? getPreferredTheme();
    const nextTheme = activeTheme === "dark" ? "light" : "dark";
    window.localStorage.setItem(THEME_KEY, nextTheme);
    setTheme(nextTheme);
    applyTheme(nextTheme);
  }

  return (
    <button
      type="button"
      aria-label="Toggle theme"
      title="Toggle theme"
      className="rs-theme-toggle fixed right-3 top-3 z-50 grid h-10 w-10 place-items-center rounded-md border border-border bg-surface/90 text-ink shadow-soft backdrop-blur transition hover:bg-cloud focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-leaf/25"
      onClick={toggleTheme}
    >
      {theme === "light" ? <Moon size={18} aria-hidden="true" /> : <Sun size={18} aria-hidden="true" />}
    </button>
  );
}
