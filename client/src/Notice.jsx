import { useEffect } from 'react';
import { AlertCircle, CheckCircle2, X } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

// Transient alert shown at top centre. notice: { type: 'success' | 'error' | 'warning', title, description } | null
export default function Notice({ notice, onClose }) {
  useEffect(() => {
    if (!notice) return;
    const id = setTimeout(onClose, notice.type === 'success' ? 3500 : 6000);
    return () => clearTimeout(id);
  }, [notice, onClose]);

  if (!notice) return null;
  const destructive = notice.type === 'error';
  const Icon = notice.type === 'success' ? CheckCircle2 : AlertCircle;
  return (
    <div className="pointer-events-none fixed inset-x-0 top-4 z-[60] flex justify-center px-4">
      <Alert variant={destructive ? 'destructive' : 'default'} role={destructive ? 'alert' : 'status'}
        className="pointer-events-auto w-full max-w-md bg-card shadow-lg">
        <Icon className={notice.type === 'success' ? 'text-emerald-600' : notice.type === 'warning' ? 'text-amber-600' : undefined} />
        <AlertTitle>{notice.title}</AlertTitle>
        {notice.description && <AlertDescription>{notice.description}</AlertDescription>}
        <button type="button" aria-label="Dismiss" onClick={onClose}
          className="absolute top-2 right-2 rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground">
          <X className="size-4" />
        </button>
      </Alert>
    </div>
  );
}
