import { useState } from 'react';
import { startOfToday } from 'date-fns';
import { api } from './api.js';
import { fieldClass, labelClass } from './fields.js';
import DatePicker from './DatePicker.jsx';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';

export default function MeetingDialog({ business, onClose, onSaved }) {
  const [date, setDate] = useState();
  const [time, setTime] = useState('09:00');
  const [notes, setNotes] = useState('');
  const [err, setErr] = useState('');

  async function submit(e) {
    e.preventDefault();
    if (!date) { setErr('Pick a date'); return; }
    const [h, m] = time.split(':').map(Number);
    const when = new Date(date.getFullYear(), date.getMonth(), date.getDate(), h, m);
    try {
      await api.addMeeting(business.id, { scheduled_at: when.toISOString(), notes });
      onSaved();
    } catch (x) { setErr(x.message); }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/50 p-4" onClick={onClose}>
      <Card className="w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={submit} className="grid gap-4">
          <CardHeader>
            <CardTitle>Schedule meeting</CardTitle>
            <CardDescription>{business.name}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            {err && <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">{err}</div>}
            <div className="grid gap-3 sm:grid-cols-2">
              <div className={labelClass}>Date
                <DatePicker date={date} onSelect={(d) => { setDate(d); setErr(''); }} minToday />
              </div>
              <label className={labelClass}>Time (your local time)
                <input className={fieldClass} type="time" required value={time} onChange={(e) => setTime(e.target.value)} />
              </label>
            </div>
            <label className={labelClass}>Notes
              <textarea className={fieldClass + ' h-auto py-2'} rows="3" value={notes} onChange={(e) => setNotes(e.target.value)} />
            </label>
          </CardContent>
          <CardFooter className="justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit">Schedule</Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
