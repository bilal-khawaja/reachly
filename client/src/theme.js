import { useCallback, useEffect, useState } from 'react';

const KEY = 'crm_theme';
const mql = () => window.matchMedia('(prefers-color-scheme: dark)');

function stored() {
  try { const v = localStorage.getItem(KEY); return v === 'dark' || v === 'light' ? v : null; } catch { return null; }
}

export function initialTheme() {
  return stored() ?? (mql().matches ? 'dark' : 'light');
}

export function applyTheme(theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark');
  document.documentElement.style.colorScheme = theme;
}

export function useTheme() {
  const [theme, setTheme] = useState(initialTheme);

  useEffect(() => { applyTheme(theme); }, [theme]);

  // Follow the OS setting until the user picks a theme explicitly.
  useEffect(() => {
    const m = mql();
    const onChange = (e) => { if (!stored()) setTheme(e.matches ? 'dark' : 'light'); };
    m.addEventListener('change', onChange);
    return () => m.removeEventListener('change', onChange);
  }, []);

  const toggle = useCallback(() => {
    setTheme((t) => {
      const next = t === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem(KEY, next); } catch { /* ignore */ }
      return next;
    });
  }, []);

  return [theme, toggle];
}
