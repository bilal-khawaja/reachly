import { Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTheme } from './theme.js';

export default function ThemeToggle({ className }) {
  const [theme, toggle] = useTheme();
  const dark = theme === 'dark';
  return (
    <Button variant="outline" size="icon" className={className} onClick={toggle}
      aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'} title={dark ? 'Light mode' : 'Dark mode'}>
      {dark ? <Sun /> : <Moon />}
    </Button>
  );
}
