const KEY = 'crm_guest';
export const GUEST_MAX_ROWS = 200;

const EMAIL_RE = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$/;
const WEBSITE_RE = /^(https?:\/\/)?([A-Za-z0-9-]+\.)+[A-Za-z]{2,}(:[0-9]+)?(\/[^\s]*)?$/;
const STATUSES = ['new', 'contacted', 'replied', 'meeting_scheduled', 'proposal_sent', 'won', 'lost'];
const CHANNELS = ['phone', 'whatsapp', 'email', 'instagram', 'linkedin', 'facebook'];

const COLUMNS = [
  { name: 'name', required: true, example: 'Acme Plumbing', hint: 'Business name' },
  { name: 'phone', required: true, example: '506-555-0100', hint: 'Max 40 chars' },
  { name: 'email', required: false, example: 'info@acme.com', hint: 'Valid email or blank' },
  { name: 'website', required: false, example: 'acme.com', hint: 'Domain or URL, or blank' },
  { name: 'business_type', required: false, example: 'plumbing', hint: 'Free text, e.g. clinic, hvac' },
  { name: 'city', required: false, example: 'Moncton', hint: 'Free text' },
  { name: 'country', required: false, example: 'Canada', hint: 'Free text' },
  { name: 'channel', required: false, example: 'phone', hint: `${CHANNELS.join(', ')} (default phone)` },
  { name: 'status', required: false, example: 'new', hint: `${STATUSES.join(', ')} (default new)` },
  { name: 'notes', required: false, example: 'Called Mon, call back Fri', hint: 'Free text' },
];
const NAMES = COLUMNS.map((c) => c.name);

let state = load();
function load() {
  try { return JSON.parse(sessionStorage.getItem(KEY)) ?? null; } catch { return null; }
}
const save = () => { try { sessionStorage.setItem(KEY, JSON.stringify(state)); } catch {} };

export const isGuest = () => state !== null;
export const guestHasData = () => !!state && (state.businesses.length > 0 || state.meetings.length > 0);
export function enterGuest() { state = { nextId: 1, businesses: [], meetings: [] }; save(); }
export function leaveGuest() { state = null; try { sessionStorage.removeItem(KEY); } catch {} }

const fail = (msg) => { throw new Error(msg); };
const blank = (v) => (v == null || String(v).trim() === '' ? null : String(v).trim());

function clean(raw, { partial = false } = {}) {
  const out = {};
  for (const k of NAMES) {
    if (partial && !(k in raw)) continue;
    out[k] = blank(raw[k]);
  }
  if (!partial || 'name' in out) { if (!out.name) fail('name required'); }
  if (!partial || 'phone' in out) {
    if (!out.phone) fail('phone: phone is required');
    if (out.phone.length > 40) fail('phone: phone is too long');
  }
  if (out.email) { if (out.email.length > 254 || !EMAIL_RE.test(out.email)) fail('email: invalid email address'); out.email = out.email.toLowerCase(); }
  if (out.website && (out.website.length > 2048 || !WEBSITE_RE.test(out.website))) fail('website: invalid website (e.g. example.com or https://example.com/page)');
  if ('channel' in out) { out.channel = (out.channel ?? 'phone').toLowerCase(); if (!CHANNELS.includes(out.channel)) fail(`channel: must be one of ${CHANNELS.join(', ')}`); }
  if ('status' in out) { out.status = (out.status ?? 'new').toLowerCase().replace(/ /g, '_'); if (!STATUSES.includes(out.status)) fail('status: invalid status'); }
  return out;
}

const now = () => new Date().toISOString();
const view = (b) => {
  const upcoming = state.meetings.filter((m) => m.business_id === b.id && !m.done && new Date(m.scheduled_at) >= new Date()).map((m) => m.scheduled_at).sort();
  return { ...b, next_meeting: upcoming[0] ?? null, meeting_count: state.meetings.filter((m) => m.business_id === b.id).length };
};
const dupKey = (b) => `${b.name.toLowerCase()}\u0000${b.phone}`;

function csvEscape(v) {
  let s = v == null ? '' : String(v);
  if (s && (/^[=@\t\r]/.test(s) || (/^[+-]/.test(s) && !/^[+-]?[\d\s().-]+$/.test(s)))) s = `'${s}`;
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
const toCsv = (rows) => [NAMES.join(','), ...rows.map((r) => NAMES.map((c) => csvEscape(r[c])).join(','))].join('\r\n');

function parseCsv(text) {
  const rows = []; let row = [], cell = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += c; }
    else if (c === '"') q = true;
    else if (c === ',') { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(cell); rows.push(row); row = []; cell = ''; }
    else cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows.map((r) => r.map((c) => c.trim()));
}

async function readImport(file) {
  if (!/\.csv$/i.test(file.name)) fail('The trial supports .csv files only. Create an account to import .xlsx.');
  if (file.size > 1024 * 1024) fail('File too large for the trial (max 1 MB)');
  const grid = parseCsv((await file.text()).replace(/^\uFEFF/, ''));
  const start = grid.findIndex((r) => r.some(Boolean));
  if (start < 0) fail('File is empty');
  const header = grid[start].map((h) => h.toLowerCase().replace(/[\s-]+/g, '_'));
  const unknown = header.filter((h) => h && !NAMES.includes(h));
  if (unknown.length) fail(`Unknown column(s): ${unknown.join(', ')}. Allowed: ${NAMES.join(', ')}`);
  const missing = ['name', 'phone'].filter((c) => !header.includes(c));
  if (missing.length) fail(`Missing required column(s): ${missing.join(', ')}`);
  const seen = new Set(state.businesses.map(dupKey));
  const rows = [];
  grid.slice(start + 1).forEach((r, i) => {
    if (!r.some(Boolean)) return;
    const raw = Object.fromEntries(header.map((h, j) => [h, r[j] ?? '']).filter(([h]) => h));
    let data = null, error = null, duplicate = false;
    try { data = clean(raw); } catch (e) { error = e.message; }
    if (data) { duplicate = seen.has(dupKey(data)); seen.add(dupKey(data)); }
    rows.push({ row: start + 2 + i, data: data ?? raw, errors: error ? [error] : [], duplicate });
  });
  if (!rows.length) fail('No data rows found under the header');
  return rows;
}

function download(text, filename) {
  const href = URL.createObjectURL(new Blob(['\uFEFF' + text], { type: 'text/csv;charset=utf-8' }));
  Object.assign(document.createElement('a'), { href, download: filename }).click();
  URL.revokeObjectURL(href);
}

export const guestApi = {
  async list(p = {}) {
    const has = (v, needle) => (v ?? '').toLowerCase().includes(needle.toLowerCase());
    return state.businesses
      .filter((b) => (!p.status || b.status === p.status)
        && (!p.city || (b.city ?? '').toLowerCase() === p.city.toLowerCase())
        && (!p.type || (b.business_type ?? '').toLowerCase() === p.type.toLowerCase())
        && (!p.no_website || !b.website)
        && (!p.q || has(b.name, p.q) || has(b.phone, p.q)))
      .map(view)
      .sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id - a.id);
  },
  async create(body) {
    if (state.businesses.length >= GUEST_MAX_ROWS) fail(`The trial is limited to ${GUEST_MAX_ROWS} businesses. Create an account for more.`);
    const b = { id: state.nextId++, ...clean(body), created_at: now(), updated_at: now() };
    b.channel ??= 'phone'; b.status ??= 'new';
    state.businesses.push(b); save();
    return view(b);
  },
  async update(id, body) {
    const b = state.businesses.find((x) => x.id === id) ?? fail('not found');
    Object.assign(b, clean(body, { partial: true }), { updated_at: now() }); save();
    return view(b);
  },
  async bulkRemove(ids) {
    const before = state.businesses.length;
    state.businesses = state.businesses.filter((b) => !ids.includes(b.id));
    state.meetings = state.meetings.filter((m) => state.businesses.some((b) => b.id === m.business_id));
    save();
    return { deleted: before - state.businesses.length };
  },
  async remove(id) { return guestApi.bulkRemove([id]); },
  async meetings() {
    return state.meetings
      .map((m) => ({ ...m, business_name: state.businesses.find((b) => b.id === m.business_id)?.name ?? '' }))
      .sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at));
  },
  async addMeeting(bid, m) {
    const b = state.businesses.find((x) => x.id === bid) ?? fail('business not found');
    const meeting = { id: state.nextId++, business_id: bid, scheduled_at: m.scheduled_at, notes: blank(m.notes), done: false, created_at: now() };
    state.meetings.push(meeting);
    if (['new', 'contacted', 'replied'].includes(b.status)) { b.status = 'meeting_scheduled'; b.updated_at = now(); }
    save();
    return meeting;
  },
  async toggleMeeting(id, done) {
    const m = state.meetings.find((x) => x.id === id) ?? fail('not found');
    m.done = done; save();
    return m;
  },
  async removeMeeting(id) { state.meetings = state.meetings.filter((m) => m.id !== id); save(); return null; },
  async exportLeads() {
    download(toCsv([...state.businesses].sort((a, b) => b.created_at.localeCompare(a.created_at))), `leads-${new Date().toISOString().slice(0, 10)}.csv`);
  },
  async importSpec() { return { columns: COLUMNS, max_rows: GUEST_MAX_ROWS, max_mb: 1 }; },
  async importTemplate() { download(`${NAMES.join(',')}\r\n${COLUMNS.map((c) => csvEscape(c.example)).join(',')}`, 'leads-template.csv'); },
  async importPreview(file) {
    const rows = await readImport(file);
    if (rows.length > GUEST_MAX_ROWS) fail(`Too many rows (${rows.length}). The trial allows ${GUEST_MAX_ROWS}.`);
    const bad = rows.filter((r) => r.errors.length);
    return {
      total: rows.length,
      valid: rows.filter((r) => !r.errors.length && !r.duplicate).length,
      duplicates: rows.filter((r) => r.duplicate).length,
      invalid: bad.length,
      sample: rows.filter((r) => !r.errors.length).slice(0, 10),
      errors: bad.slice(0, 100).map((r) => ({ row: r.row, messages: r.errors })),
    };
  },
  async importCommit(file) {
    const rows = await readImport(file);
    const good = rows.filter((r) => !r.errors.length && !r.duplicate);
    if (state.businesses.length + good.length > GUEST_MAX_ROWS) fail(`The trial is limited to ${GUEST_MAX_ROWS} businesses. Create an account for more.`);
    for (const r of good) state.businesses.push({ id: state.nextId++, ...r.data, created_at: now(), updated_at: now() });
    save();
    return { imported: good.length, skipped_duplicates: rows.filter((r) => r.duplicate).length, skipped_invalid: rows.filter((r) => r.errors.length).length };
  },
};
