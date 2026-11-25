import { useCallback, useEffect, useState } from 'react';

const KEY = 'crm_theme';
let fadeTimer;
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

  useEffect(() => {
    const m = mql();
    const onChange = (e) => { if (!stored()) setTheme(e.matches ? 'dark' : 'light'); };
    m.addEventListener('change', onChange);
    return () => m.removeEventListener('change', onChange);
  }, []);

  const toggle = useCallback(() => {
    const root = document.documentElement;
    root.classList.add('theme-switching');
    clearTimeout(fadeTimer);
    fadeTimer = setTimeout(() => root.classList.remove('theme-switching'), 80);
    setTheme((t) => {
      const next = t === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem(KEY, next); } catch {}
      return next;
    });
  }, []);

  return [theme, toggle];
}
