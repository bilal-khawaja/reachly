import { guestApi, isGuest } from './guest.js';

try { localStorage.removeItem('crm_token'); } catch {}
const loggedOut = () => window.dispatchEvent(new Event('crm-logout'));

async function req(method, url, body) {
  const headers = {};
  if (body) headers['Content-Type'] = 'application/json';
  const res = await fetch(url, { method, headers, credentials: 'same-origin', body: body ? JSON.stringify(body) : undefined });
  if (res.status === 401 && !/\/auth\/(login|signup|me)$/.test(url)) loggedOut();
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    if (!body && res.status >= 500) throw new Error('Cannot reach the API. Start it with `just backend`.');
    const d = body?.detail;
    throw new Error(body?.error || (typeof d === 'string' ? d : Array.isArray(d) ? d.map((x) => `${x.loc?.at(-1) ?? 'field'}: ${String(x.msg).replace(/^Value error, /, '')}`).join('; ') : null) || res.statusText);
  }
  return res.status === 204 ? null : res.json();
}

async function upload(url, file) {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(url, { method: 'POST', credentials: 'same-origin', body: fd });
  if (res.status === 401) loggedOut();
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const d = body?.detail;
    throw new Error((typeof d === 'string' ? d : Array.isArray(d) ? d.map((x) => x.msg).join('; ') : null) || (res.status >= 500 ? 'Cannot reach the API. Start it with `just backend`.' : res.statusText));
  }
  return body;
}

async function download(url, filename, errMsg) {
  const res = await fetch(url, { credentials: 'same-origin' });
  if (res.status === 401) loggedOut();
  if (!res.ok) throw new Error(errMsg);
  const href = URL.createObjectURL(await res.blob());
  Object.assign(document.createElement('a'), { href, download: filename }).click();
  URL.revokeObjectURL(href);
}

const downloadTemplate = () => download('/api/import/template', 'leads-template.csv', 'Could not download template');
const exportLeads = () => download('/api/export', `leads-${new Date().toISOString().slice(0, 10)}.csv`, 'Could not export leads');

const serverApi = {
  importSpec: () => req('GET', '/api/import/spec'),
  importTemplate: downloadTemplate,
  exportLeads,
  importPreview: (file) => upload('/api/import/preview', file),
  importCommit: (file) => upload('/api/import', file),
  me: () => req('GET', '/api/auth/me'),
  logout: () => req('POST', '/api/auth/logout'),
  logoutAll: () => req('POST', '/api/auth/logout-all'),
  login: (email, password) => req('POST', '/api/auth/login', { email, password }),
  inviteInfo: (token) => req('GET', `/api/auth/invite/${encodeURIComponent(token)}`),
  signup: (token, password) => req('POST', '/api/auth/signup', { token, password }),
  list: (params = {}) => req('GET', '/api/businesses?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v))),
  create: (b) => req('POST', '/api/businesses', b),
  update: (id, b) => req('PUT', `/api/businesses/${id}`, b),
  bulkRemove: (ids) => req('POST', '/api/businesses/bulk-delete', { ids }),
  remove: (id) => req('DELETE', `/api/businesses/${id}`),
  meetings: () => req('GET', '/api/meetings'),
  addMeeting: (id, m) => req('POST', `/api/businesses/${id}/meetings`, m),
  toggleMeeting: (id, done) => req('PATCH', `/api/meetings/${id}`, { done }),
  removeMeeting: (id) => req('DELETE', `/api/meetings/${id}`),
};

const GUEST_ONLY_OK = new Set(Object.keys(guestApi));
export const api = new Proxy(serverApi, {
  get: (t, k) => (isGuest() && GUEST_ONLY_OK.has(k) ? guestApi[k] : t[k]),
});

export const STATUSES = ['new', 'contacted', 'replied', 'meeting_scheduled', 'proposal_sent', 'won', 'lost'];
export const CHANNELS = ['phone', 'whatsapp', 'email', 'instagram', 'linkedin', 'facebook'];
export const TYPES = ['clinic', 'dental', 'vet', 'hvac', 'plumbing', 'auto repair', 'landscaping', 'restaurant', 'hotel', 'gym', 'school', 'other'];
export const label = (s) => s.replace(/_/g, ' ');
