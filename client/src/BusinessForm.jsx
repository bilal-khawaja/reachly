import { useState } from 'react';
import { api, STATUSES, CHANNELS, TYPES, label } from './api.js';
import { fieldClass, labelClass } from './fields.js';
import { SelectCombo, SuggestCombo } from './ComboField.jsx';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';

const CHANNEL_OPTIONS = CHANNELS.map((c) => ({ value: c, label: c }));
const STATUS_OPTIONS = STATUSES.map((s) => ({ value: s, label: label(s) }));
const EMPTY = { name: '', phone: '', email: '', website: '', business_type: '', city: '', country: '', channel: 'phone', status: 'new', notes: '' };

export default function BusinessForm({ initial, onClose, onSaved }) {
  const [f, setF] = useState({ ...EMPTY, ...Object.fromEntries(Object.entries(initial).filter(([, v]) => v != null)) });
  const [err, setErr] = useState('');
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    try {
      const body = Object.fromEntries(Object.keys(EMPTY).map((k) => [k, f[k]]));
      initial.id ? await api.update(initial.id, body) : await api.create(body);
      onSaved();
    } catch (x) { setErr(x.message); }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/50 p-4" onClick={onClose}>
      <Card className="w-full max-w-xl" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={submit} className="grid gap-4">
          <CardHeader>
            <CardTitle>{initial.id ? 'Edit business' : 'Add business'}</CardTitle>
            <CardDescription>{initial.id ? 'Update details for this business.' : 'Add a new prospect to your pipeline.'}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            {err && <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">{err}</div>}
            <label className={labelClass}>Business name *
              <input className={fieldClass} required autoFocus value={f.name} onChange={set('name')} />
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className={labelClass}>Phone *<input className={fieldClass} required type="tel" value={f.phone} onChange={set('phone')} /></label>
              <label className={labelClass}>Email<input className={fieldClass} type="email" placeholder="None" value={f.email} onChange={set('email')} /></label>
            </div>
            <label className={labelClass}>Website / profile link
              <input className={fieldClass} placeholder="None (e.g. example.com)" value={f.website} onChange={set('website')} />
            </label>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className={labelClass}>Business type
                <SuggestCombo options={TYPES} value={f.business_type} onChange={(v) => setF((s) => ({ ...s, business_type: v }))} placeholder="Select or type" />
              </div>
              <label className={labelClass}>City<input className={fieldClass} value={f.city} onChange={set('city')} /></label>
              <label className={labelClass}>Country<input className={fieldClass} value={f.country} onChange={set('country')} /></label>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className={labelClass}>Channel
                <SelectCombo options={CHANNEL_OPTIONS} value={f.channel} onChange={(v) => setF((s) => ({ ...s, channel: v }))} placeholder="Channel" />
              </div>
              <div className={labelClass}>Status
                <SelectCombo options={STATUS_OPTIONS} value={f.status} onChange={(v) => setF((s) => ({ ...s, status: v }))} placeholder="Status" />
              </div>
            </div>
            <label className={labelClass}>Notes
              <textarea className={fieldClass + ' h-auto py-2'} rows="3" value={f.notes} onChange={set('notes')} />
            </label>
          </CardContent>
          <CardFooter className="justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit">Save</Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
