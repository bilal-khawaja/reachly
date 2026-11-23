import { useEffect, useRef, useState } from 'react';
import { Download, FileSpreadsheet } from 'lucide-react';
import { Chip } from '@heroui/react';
import { api } from './api.js';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

const Err = ({ children }) => (
  <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">{children}</div>
);

export default function ImportDialog({ onClose, onImported }) {
  const [spec, setSpec] = useState(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const input = useRef(null);

  useEffect(() => { api.importSpec().then(setSpec).catch((e) => setErr(e.message)); }, []);

  async function pick(f) {
    setErr(''); setPreview(null); setFile(null);
    if (!f) return;
    setBusy(true);
    try {
      setPreview(await api.importPreview(f));
      setFile(f);
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); if (input.current) input.current.value = ''; }
  }

  async function confirm() {
    setBusy(true); setErr('');
    try { onImported(await api.importCommit(file)); }
    catch (e) { setErr(e.message); setBusy(false); }
  }

  const download = () => api.importTemplate().catch((e) => setErr(e.message));
  const cols = spec?.columns ?? [];
  const shown = cols.map((c) => c.name);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/50 p-4" onClick={onClose}>
      <Card className="w-full max-w-4xl" onClick={(e) => e.stopPropagation()}>
        <CardHeader>
          <CardTitle>Import businesses</CardTitle>
          <CardDescription>
            Upload a .csv or .xlsx{spec ? ` (max ${spec.max_rows} rows, ${spec.max_mb} MB)` : ''}. Row 1 must be a header using only the allowed columns. Unknown columns are rejected.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          {err && <Err>{err}</Err>}

          <div className="flex flex-wrap items-start gap-8">
            <div className="grid w-48 shrink-0 justify-items-center gap-2">
              <button type="button" onClick={download} aria-label="Download sample file" title="Download sample file"
                className="group w-full overflow-hidden rounded-lg border bg-background text-left shadow-sm transition hover:border-primary hover:shadow-md">
                <div className="flex items-center justify-between bg-emerald-600 px-2 py-1 text-[10px] font-semibold text-white">
                  <span>CSV</span>
                </div>
                <div className="grid gap-px bg-border p-px" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' }}>
                  {cols.slice(0, 3).map((c) => <div key={c.name} className="truncate bg-muted px-1 py-0.5 font-mono text-[9px] font-medium">{c.name}</div>)}
                  {[0, 1, 2, 3].flatMap((r) => cols.slice(0, 3).map((c) => (
                    <div key={`${r}-${c.name}`} className="truncate bg-background px-1 py-0.5 text-[9px] text-muted-foreground">{r === 0 ? c.example : <span className="block h-1.5 w-3/4 rounded bg-muted" />}</div>
                  )))}
                </div>
                <div className="px-2 py-1 text-center text-[9px] text-muted-foreground">+ {Math.max(cols.length - 3, 0)} more columns</div>
              </button>
              <span className="max-w-full truncate text-xs font-medium">leads-template.csv</span>
            </div>

            <div className="grid min-w-0 flex-1 gap-3 text-sm">
              <div>
                <div className="mb-2 text-xs font-medium text-muted-foreground">Columns allowed (exact names)</div>
                <div className="flex flex-wrap gap-2.5">
                  {cols.map((c) => (
                    <span key={c.name} title={c.hint}>
                      <Chip color="accent" variant="soft" size="lg" className="bg-[color-mix(in_oklab,var(--blue)_14%,transparent)] text-[var(--blue)]">
                        <Chip.Label className="font-sans text-sm font-bold text-[var(--blue)]">{c.name}{c.required && ' *'}</Chip.Label>
                      </Chip>
                    </span>
                  ))}
                </div>
                <div className="mt-3 text-xs text-muted-foreground">* required. Hover a column for format hints.</div>
              </div>
            </div>
          </div>

          {preview && (
            <div className="grid gap-3">
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
                <span><b>{preview.valid}</b> will be imported</span>
                {preview.duplicates > 0 && <span className="text-muted-foreground"><b>{preview.duplicates}</b> duplicates skipped</span>}
                {preview.invalid > 0 && <span className="text-destructive"><b>{preview.invalid}</b> invalid skipped</span>}
                <span className="text-muted-foreground">of {preview.total} rows</span>
              </div>

              {preview.sample.length > 0 && (
                <div className="overflow-x-auto rounded-lg border">
                  <Table className="min-w-max">
                    <TableHeader><TableRow><TableHead>Row</TableHead>{shown.map((k) => <TableHead key={k} className="font-mono text-xs">{k}</TableHead>)}</TableRow></TableHeader>
                    <TableBody>
                      {preview.sample.map((r) => (
                        <TableRow key={r.row} className={r.duplicate ? 'opacity-50' : ''}>
                          <TableCell className="text-muted-foreground">{r.row}</TableCell>
                          {shown.map((k) => <TableCell key={k} className="max-w-48 truncate text-xs">{r.data[k] ?? '—'}</TableCell>)}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
              {preview.sample.length > 0 && <p className="text-xs text-muted-foreground">Showing first {preview.sample.length} valid rows.</p>}

              {preview.errors.length > 0 && (
                <div className="max-h-40 overflow-y-auto rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-xs">
                  {preview.errors.map((e) => <div key={e.row}><b>Row {e.row}:</b> {e.messages.join('; ')}</div>)}
                  {preview.invalid > preview.errors.length && <div className="mt-1 text-muted-foreground">…and {preview.invalid - preview.errors.length} more</div>}
                </div>
              )}
            </div>
          )}
        </CardContent>
        <CardFooter className="flex-wrap justify-between gap-2">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <Button type="button" variant="outline" onClick={download}><Download className="size-4" /> Download preview</Button>
            <Button type="button" disabled={busy} onClick={() => input.current?.click()}>
              <FileSpreadsheet className="size-4" /> {file ? 'Change file' : 'Upload'}
            </Button>
            <input ref={input} type="file" hidden accept=".csv,.xlsx" onChange={(e) => pick(e.target.files?.[0])} />
            {file && <span className="max-w-48 truncate text-sm text-muted-foreground">{file.name}</span>}
            {busy && !file && <span className="text-sm text-muted-foreground">Checking…</span>}
          </div>
          <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
          <Button type="button" disabled={busy || !file || !preview?.valid} onClick={confirm}>
            {preview?.valid ? `Import ${preview.valid} business${preview.valid > 1 ? 'es' : ''}` : 'Import'}
          </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
