"use client";

import { useEffect, useRef } from "react";

type ThemePreference = "light" | "dark" | "auto";

function applyTheme(preference: ThemePreference) {
  const dark = preference === "dark" || (preference === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  document.documentElement.dataset.themePreference = preference;
  document.documentElement.style.colorScheme = dark ? "dark" : "light";
}

export function ThemeSwitcher({ mobile = false }: { mobile?: boolean }) {
  const select = useRef<HTMLSelectElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem("vr-theme");
    const selected: ThemePreference = stored === "light" || stored === "dark" ? stored : "auto";
    if (select.current) select.current.value = selected;
    applyTheme(selected);
    const media = matchMedia("(prefers-color-scheme: dark)");
    const sync = () => !localStorage.getItem("vr-theme") && applyTheme("auto");
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);

  function change(value: ThemePreference) {
    if (value === "auto") localStorage.removeItem("vr-theme"); else localStorage.setItem("vr-theme", value);
    applyTheme(value);
  }

  return <label className={`theme-switcher ${mobile ? "theme-switcher-mobile" : ""}`}>
    <span>{mobile ? "Theme" : <span className="sr-only">Color theme</span>}</span>
    <select ref={select} aria-label="Color theme" defaultValue="auto" onChange={(event) => change(event.target.value as ThemePreference)}>
      <option value="light">Light</option><option value="dark">Dark</option><option value="auto">Auto</option>
    </select>
  </label>;
}
