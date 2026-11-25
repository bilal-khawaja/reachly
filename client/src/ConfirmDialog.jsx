import { useEffect } from 'react';
import { Alert as HeroAlert } from '@heroui/react';
import { Button } from '@/components/ui/button';

export default function ConfirmDialog({ title, description, confirmLabel = 'Delete', onConfirm, onCancel }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onCancel(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onCancel]);

  return (
    <div className="fixed inset-0 z-[70] grid place-items-center bg-black/30 p-4 backdrop-blur-[3px] animate-in fade-in duration-200 motion-reduce:animate-none" onClick={onCancel}>
      <div className="flex w-full justify-center">
        <HeroAlert status="danger" role="alertdialog" className="w-full max-w-md !bg-neutral-900 shadow-2xl animate-in fade-in zoom-in-95 slide-in-from-bottom-2 duration-300 ease-out motion-reduce:animate-none" onClick={(e) => e.stopPropagation()}>
          <HeroAlert.Indicator />
          <HeroAlert.Content>
            <HeroAlert.Title className="font-normal text-red-600 dark:text-red-400">{title}</HeroAlert.Title>
            {description && <HeroAlert.Description className="text-white">{description}</HeroAlert.Description>}
            <div className="mt-3 flex gap-2">
              <Button size="sm" variant="destructive" autoFocus onClick={onConfirm}>{confirmLabel}</Button>
              <Button size="sm" variant="outline" onClick={onCancel}>Cancel</Button>
            </div>
          </HeroAlert.Content>
        </HeroAlert>
      </div>
    </div>
  );
}
