const KEY = 'crm_token';
export const getToken = () => { try { return localStorage.getItem(KEY); } catch { return null; } };
export const setToken = (t) => { try { t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY); } catch { /* ignore */ } };

async function req(method, url, body) {
  const headers = {};
  if (body) headers['Content-Type'] = 'application/json';
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined });
  if (res.status === 401 && !/\/auth\/(login|signup)$/.test(url)) {
    setToken(null);
    window.dispatchEvent(new Event('crm-logout'));
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    // Vite's proxy answers with a plain-text 5xx when the backend is down.
    if (!body && res.status >= 500) throw new Error('Cannot reach the API. Start it with `just backend`.');
    const d = body?.detail;
    throw new Error(body?.error || (typeof d === 'string' ? d : Array.isArray(d) ? d.map((x) => `${x.loc?.at(-1) ?? 'field'}: ${String(x.msg).replace(/^Value error, /, '')}`).join('; ') : null) || res.statusText);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  login: (email, password) => req('POST', '/api/auth/login', { email, password }),
  signup: (email, password) => req('POST', '/api/auth/signup', { email, password }),
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

export const STATUSES = ['new', 'contacted', 'replied', 'meeting_scheduled', 'proposal_sent', 'won', 'lost'];
export const CHANNELS = ['phone', 'whatsapp', 'email', 'instagram', 'linkedin', 'facebook'];
export const TYPES = ['clinic', 'dental', 'vet', 'hvac', 'plumbing', 'auto repair', 'landscaping', 'restaurant', 'hotel', 'gym', 'school', 'other'];
export const label = (s) => s.replace(/_/g, ' ');
