import { useEffect, useState, useCallback } from 'react';
import { api, STATUSES, label, getToken, setToken } from './api.js';
import BusinessForm from './BusinessForm.jsx';
import MeetingDialog from './MeetingDialog.jsx';
import ImportDialog from './ImportDialog.jsx';
import Login from './Login.jsx';
import GridBackground from '@/components/GridBackground';
import { Button } from '@/components/ui/button';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { NavigationMenu, NavigationMenuItem, NavigationMenuLink, NavigationMenuList, navigationMenuTriggerStyle } from '@/components/ui/navigation-menu';
import { Checkbox } from '@/components/ui/checkbox';
import { LogOut, Pencil, Trash2 } from 'lucide-react';
import ConfirmDialog from './ConfirmDialog.jsx';
import Notice from './Notice.jsx';
import ThemeToggle from './ThemeToggle.jsx';
import { SelectCombo } from './ComboField.jsx';
import { cn } from '@/lib/utils';

const STATUS_OPTIONS = STATUSES.map((s) => ({ value: s, label: label(s) }));
const fmt = (d) => (d ? new Date(d).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : '—');

// Stop diagonal ("circular") scrolling in table viewports: when a wheel/trackpad event moves both axes,
// keep only the dominant one. Single-axis events are left to the browser (native smooth scrolling).
function axisLock(el) {
  if (!el || el._axisLock) return;
  el._axisLock = true;
  el.addEventListener('wheel', (e) => {
    if (e.ctrlKey || !e.deltaX || !e.deltaY) return;
    const vp = el.querySelector('[data-slot=scroll-area-viewport]');
    if (!vp) return;
    const horizontal = Math.abs(e.deltaX) > Math.abs(e.deltaY);
    const d = horizontal ? e.deltaX : e.deltaY;
    const pos = horizontal ? vp.scrollLeft : vp.scrollTop;
    const max = horizontal ? vp.scrollWidth - vp.clientWidth : vp.scrollHeight - vp.clientHeight;
    if (max <= 0 || (d < 0 && pos <= 0) || (d > 0 && pos >= max)) return; // at an edge: let the page handle it
    e.preventDefault();
    vp.scrollBy({ [horizontal ? 'left' : 'top']: d });
  }, { passive: false });
}

export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  useEffect(() => {
    const out = () => setAuthed(false);
    window.addEventListener('crm-logout', out);
    return () => window.removeEventListener('crm-logout', out);
  }, []);
  if (!authed) return <Login onLogin={() => setAuthed(true)} />;
  return <Crm onLogout={() => { setToken(null); setAuthed(false); }} />;
}

function Crm({ onLogout }) {
  const [rows, setRows] = useState([]);
  const [meetings, setMeetings] = useState([]);
  const [filters, setFilters] = useState({ city: '', type: '', q: '', no_website: '' });
  const [statusTab, setStatusTab] = useState('all');
  const [page, setPage] = useState('clients');
  const [editing, setEditing] = useState(null);
  const [scheduling, setScheduling] = useState(null);
  const [importing, setImporting] = useState(false);
  const [notice, setNotice] = useState(null);
  const [confirming, setConfirming] = useState(null);
  // Fade edges for the leads rows only (header stays crisp): top fade sits just below the sticky header.
  const [fade, setFade] = useState({ top: false, bottom: false });
  const onRowsScroll = useCallback((e) => {
    const el = e.currentTarget;
    const top = el.scrollTop > 2, bottom = el.scrollTop + el.clientHeight < el.scrollHeight - 2;
    setFade((f) => (f.top === top && f.bottom === bottom ? f : { top, bottom }));
  }, []);
  const notify = useCallback((type, title, description) => setNotice({ type, title, description }), []);
  const closeNotice = useCallback(() => setNotice(null), []);
  const setError = useCallback((msg) => msg && notify('error', 'Something went wrong', msg), [notify]);
  const [selected, setSelected] = useState(() => new Set());
  const [selectMode, setSelectMode] = useState(false);

  const load = useCallback(async () => {
    try {
      const [b, m] = await Promise.all([api.list(filters), api.meetings()]);
      setRows(b);
      setMeetings(m);
      setSelected((s) => new Set([...s].filter((id) => b.some((r) => r.id === id))));
    } catch (e) {
      setError(e.message);
    }
  }, [filters, setError]);

  useEffect(() => { load(); }, [load]);

  const visible = statusTab === 'all' ? rows : rows.filter((r) => r.status === statusTab);
  const selectedVisible = visible.filter((r) => selected.has(r.id));
  const allSelected = visible.length > 0 && selectedVisible.length === visible.length;
  const toggleOne = (id, on) => setSelected((s) => { const n = new Set(s); on ? n.add(id) : n.delete(id); return n; });
  const toggleAll = (on) => setSelected(on ? new Set(visible.map((r) => r.id)) : new Set());
  function editSelected() {
    if (selectedVisible.length > 1) {
      notify('warning', 'Only one row can be edited at a time', `You have ${selectedVisible.length} rows selected. Select a single row to edit it.`);
      return;
    }
    setEditing(selectedVisible[0]);
  }
  const exitSelect = () => { setSelectMode(false); setSelected(new Set()); };
  function deleteSelected() {
    const ids = selectedVisible.map((r) => r.id);
    if (!ids.length) return;
    setConfirming({
      title: `Delete ${ids.length} ${ids.length > 1 ? 'leads' : 'lead'}?`,
      description: 'If you confirm, they will be permanently deleted along with their meetings.',
      run: async () => {
        try {
          await api.bulkRemove(ids);
          setSelected(new Set());
          load();
          notify('deleted', ids.length > 1 ? `${ids.length} businesses deleted` : 'Business deleted', 'Their meetings were removed too.');
        } catch (e) { setError(e.message); }
      },
    });
  }
  const setF = (k) => (e) => setFilters({ ...filters, [k]: e.target.value });
  const input = 'h-9 rounded-lg border border-input bg-background px-3 text-sm outline-none blue-glow';
  const navLink = (id) => cn(navigationMenuTriggerStyle(), 'cursor-pointer !px-0 hover:!bg-transparent focus:!bg-transparent data-active:!bg-transparent focus-visible:!ring-0', page === id ? 'text-foreground' : 'text-muted-foreground hover:text-foreground');

  return (
    <ScrollArea className="h-screen">
    <div className="relative min-h-screen text-foreground">
      <GridBackground />
      <header className="sticky top-0 z-40 px-4 pt-3">
        <div className="glass-nav relative mx-auto flex w-full max-w-7xl items-center gap-4 rounded-2xl px-6 py-3">
          <span className="text-3xl font-semibold tracking-tight" style={{ fontFamily: "'Geist Brand', sans-serif" }}>Reachly</span>
          <NavigationMenu className="ml-8 max-w-none flex-none">
            <NavigationMenuList className="gap-6">
              <NavigationMenuItem>
                <NavigationMenuLink href="#clients" active={page === 'clients'} aria-current={page === 'clients' ? 'page' : undefined} className={navLink('clients')} onClick={(e) => { e.preventDefault(); setPage('clients'); }}>
                  Dashboard
                </NavigationMenuLink>
              </NavigationMenuItem>
              <NavigationMenuItem>
                <NavigationMenuLink href="#meetings" active={page === 'meetings'} aria-current={page === 'meetings' ? 'page' : undefined} className={navLink('meetings')} onClick={(e) => { e.preventDefault(); setPage('meetings'); }}>
                  Meetings
                </NavigationMenuLink>
              </NavigationMenuItem>
            </NavigationMenuList>
          </NavigationMenu>
          <div className="flex-1" />
          <Button variant="outline" onClick={() => setImporting(true)}>Import</Button>
          <Button onClick={() => setEditing({})}>+ Add business</Button>
          <Button variant="outline" size="icon" onClick={onLogout} aria-label="Log out" title="Log out"><LogOut /></Button>
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-4 px-4 pb-6 pt-12">

        {page === 'clients' && (
          <>
            <Tabs value={statusTab} onValueChange={(v) => { setStatusTab(v); setSelected(new Set()); }}>
              <div className="flex justify-center overflow-x-auto pb-1">
                <TabsList>
                  <TabsTrigger value="all" className="px-3">All</TabsTrigger>
                  {STATUSES.map((s) => (
                    <TabsTrigger key={s} value={s} className="px-3 capitalize">{label(s)}</TabsTrigger>
                  ))}
                </TabsList>
              </div>
            </Tabs>

            <div className="flex min-h-9 flex-wrap items-center justify-center gap-2">
              <input className={cn(input, 'w-56')} placeholder="Search name / phone" value={filters.q} onChange={setF('q')} />
              <input className={cn(input, 'w-36')} placeholder="City" value={filters.city} onChange={setF('city')} />
              <input className={cn(input, 'w-40')} placeholder="Business type" value={filters.type} onChange={setF('type')} />
              <Button variant={filters.no_website ? 'secondary' : 'outline'} className="h-9" aria-pressed={!!filters.no_website}
                onClick={() => setFilters({ ...filters, no_website: filters.no_website ? '' : 'true' })}>
                No website
              </Button>
              <Button variant={selectMode ? 'secondary' : 'outline'} className="h-9" onClick={() => (selectMode ? exitSelect() : setSelectMode(true))}>
                {selectMode ? 'Cancel' : 'Select'}
              </Button>
              {selectMode && selectedVisible.length > 0 && (
                <div className="flex items-center gap-1 pl-1">
                  <span className="text-sm text-muted-foreground">{selectedVisible.length} selected</span>
                  <Button variant="ghost" size="icon" aria-label="Edit selected" title="Edit selected" onClick={editSelected}>
                    <Pencil className="size-4" />
                  </Button>
                  <Button variant="ghost" size="icon" aria-label="Delete selected" title="Delete selected"
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive" onClick={deleteSelected}>
                    <Trash2 className="size-5" />
                  </Button>
                </div>
              )}
            </div>

            <div className="rounded-lg border bg-card">
              <div className="relative" onScrollCapture={(e) => onRowsScroll({ currentTarget: e.target })}
                ref={(el) => { axisLock(el); const vp = el?.querySelector('[data-slot=scroll-area-viewport]'); if (vp) onRowsScroll({ currentTarget: vp }); }}>
              <ScrollArea className="max-h-[70vh] [&>[data-slot=scroll-area-viewport]]:max-h-[70vh]">
              <Table className="min-w-max">
                <TableHeader className="[&_th]:sticky [&_th]:top-0 [&_th]:z-10 [&_th]:bg-card [&_th]:shadow-[inset_0_-1px_0_var(--border)]">
                  <TableRow>
                    {selectMode && <TableHead className="w-10" />}
                    <TableHead className="text-center">Business</TableHead><TableHead>Website</TableHead><TableHead className="text-center">Phone</TableHead><TableHead>Type</TableHead>
                    <TableHead className="text-center">City</TableHead><TableHead>Channel</TableHead><TableHead className="text-center">Status</TableHead>
                    <TableHead>Next meeting</TableHead><TableHead className="text-center">Notes / reminders</TableHead><TableHead className="px-6 text-center">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visible.map((r) => (
                    <TableRow key={r.id} data-state={selected.has(r.id) ? 'selected' : undefined}>
                      {selectMode && (
                        <TableCell>
                          <Checkbox aria-label={`Select ${r.name}`} checked={selected.has(r.id)} onCheckedChange={(on) => toggleOne(r.id, on)} />
                        </TableCell>
                      )}
                      <TableCell className="pl-6 font-medium">{r.name}</TableCell>
                      <TableCell>{r.website ? <a href={/^https?:\/\//i.test(r.website) ? r.website : `https://${r.website}`} target="_blank" rel="noreferrer" className="text-primary underline-offset-4 hover:underline">{r.website}</a> : <span className="text-muted-foreground">None</span>}</TableCell>
                      <TableCell>{r.phone || '—'}{r.email && <div className="text-xs text-muted-foreground">{r.email}</div>}</TableCell>
                      <TableCell className="capitalize">{r.business_type || '—'}</TableCell>
                      <TableCell>{r.city || '—'}{r.country && <div className="text-xs text-muted-foreground">{r.country}</div>}</TableCell>
                      <TableCell className="capitalize">{r.channel}</TableCell>
                      <TableCell>
                        <div className="w-44">
                          <SelectCombo options={STATUS_OPTIONS} value={r.status} placeholder="Status" className="[&_input]:text-center"
                            onChange={async (v) => { try { await api.update(r.id, { status: v }); load(); } catch (e) { setError(e.message); } }} />
                        </div>
                      </TableCell>
                      <TableCell className={`whitespace-nowrap text-muted-foreground${r.next_meeting ? '' : ' text-center'}`}>{fmt(r.next_meeting)}</TableCell>
                      <TableCell className={`max-w-64 whitespace-normal break-words text-sm text-muted-foreground${r.notes ? '' : ' text-center'}`}>{r.notes || '—'}</TableCell>
                      <TableCell className="whitespace-nowrap px-6 text-center">
                        <Button size="sm" variant="outline" onClick={() => setScheduling(r)}>Schedule</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {!visible.length && <TableRow><TableCell colSpan={selectMode ? 11 : 10} className="py-10 text-center text-muted-foreground">No businesses here yet.</TableCell></TableRow>}
                </TableBody>
              </Table>
              <ScrollBar orientation="horizontal" />
              </ScrollArea>
              <div aria-hidden className={`pointer-events-none absolute inset-x-0 top-10 z-20 h-8 bg-gradient-to-b from-card to-transparent transition-opacity ${fade.top ? 'opacity-100' : 'opacity-0'}`} />
              <div aria-hidden className={`pointer-events-none absolute inset-x-0 bottom-0 z-20 h-8 rounded-b-lg bg-gradient-to-t from-card to-transparent transition-opacity ${fade.bottom ? 'opacity-100' : 'opacity-0'}`} />
              </div>
            </div>
          </>
        )}

        {page === 'meetings' && (
          <div className="rounded-lg border bg-card" ref={axisLock}>
            <ScrollArea className="w-full max-h-[70vh] [&>[data-slot=scroll-area-viewport]]:max-h-[70vh]">
            <Table className="min-w-max">
              <TableHeader className="[&_th]:sticky [&_th]:top-0 [&_th]:z-10 [&_th]:bg-card [&_th]:shadow-[inset_0_-1px_0_var(--border)]">
                <TableRow><TableHead>When</TableHead><TableHead>Business</TableHead><TableHead>Notes</TableHead><TableHead>Done</TableHead><TableHead /></TableRow>
              </TableHeader>
              <TableBody>
                {meetings.map((m) => (
                  <TableRow key={m.id} className={m.done ? 'opacity-50' : ''}>
                    <TableCell className="whitespace-nowrap">{fmt(m.scheduled_at)}</TableCell>
                    <TableCell className="font-medium">{m.business_name}</TableCell>
                    <TableCell className="whitespace-normal text-muted-foreground">{m.notes || '—'}</TableCell>
                    <TableCell><input type="checkbox" className="size-4" checked={m.done} onChange={async (e) => { await api.toggleMeeting(m.id, e.target.checked); load(); }} /></TableCell>
                    <TableCell className="text-right"><Button size="sm" variant="ghost" className="text-destructive" onClick={() => setConfirming({ title: 'Delete this meeting?', description: 'If you confirm, it will be permanently deleted.', run: async () => { try { await api.removeMeeting(m.id); load(); notify('deleted', 'Meeting deleted'); } catch (e) { setError(e.message); } } })}>Delete</Button></TableCell>
                  </TableRow>
                ))}
                {!meetings.length && <TableRow><TableCell colSpan={5} className="py-10 text-center text-muted-foreground">No meetings scheduled.</TableCell></TableRow>}
              </TableBody>
            </Table>
            <ScrollBar orientation="horizontal" />
            </ScrollArea>
          </div>
        )}
      </main>

      <Notice notice={notice} onClose={closeNotice} />
      {confirming && <ConfirmDialog title={confirming.title} description={confirming.description} onCancel={() => setConfirming(null)} onConfirm={() => { const run = confirming.run; setConfirming(null); run(); }} />}
      {editing && <BusinessForm initial={editing} onClose={() => setEditing(null)} onSaved={() => { const edited = !!editing.id; setEditing(null); setSelected(new Set()); load(); notify('success', edited ? 'Business updated' : 'Business added'); }} />}
      {importing && (
        <ImportDialog
          onClose={() => setImporting(false)}
          onImported={(r) => {
            setImporting(false); load();
            const skipped = [r.skipped_duplicates && `${r.skipped_duplicates} duplicates`, r.skipped_invalid && `${r.skipped_invalid} invalid`].filter(Boolean).join(', ');
            notify('success', `${r.imported} business${r.imported === 1 ? '' : 'es'} imported`, skipped ? `Skipped ${skipped}.` : undefined);
          }}
        />
      )}
      {scheduling && <MeetingDialog business={scheduling} onClose={() => setScheduling(null)} onSaved={() => { const name = scheduling.name; setScheduling(null); load(); notify('success', 'Meeting scheduled', name); }} />}
    </div>
    </ScrollArea>
  );
}
