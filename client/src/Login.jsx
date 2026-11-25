import { useEffect, useState } from 'react';
import { Form, TextField, Label, Input, FieldError } from '@heroui/react';
import { api } from './api.js';
import { enterGuest } from './guest.js';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import GridBackground from '@/components/GridBackground';
import ThemeToggle from './ThemeToggle.jsx';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const inputClass = 'blue-glow w-full border border-input shadow-none';

export default function Login({ onLogin, onGuest }) {
  const [token] = useState(() => new URLSearchParams(window.location.search).get('invite'));
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteState, setInviteState] = useState(token ? 'checking' : 'none');
  const [errors, setErrors] = useState({});
  const [formErr, setFormErr] = useState('');
  const [busy, setBusy] = useState(false);
  const signup = inviteState === 'ok';

  useEffect(() => {
    if (!token) return;
    api.inviteInfo(token).then((r) => { setInviteEmail(r.email); setInviteState('ok'); }).catch(() => setInviteState('bad'));
  }, [token]);

  function leaveInvite() {
    window.history.replaceState(null, '', window.location.pathname);
    setInviteState('none');
    setErrors({});
    setFormErr('');
  }

  async function submit(e) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.currentTarget));
    const email = signup ? inviteEmail : String(data.email).trim();
    const password = String(data.password);
    if (signup && password !== data.confirm) {
      setErrors({ confirm: 'Passwords do not match.' });
      return;
    }
    setErrors({});
    setFormErr('');
    setBusy(true);
    try {
      await (signup ? api.signup(token, password) : api.login(email, password));
      window.history.replaceState(null, '', window.location.pathname);
      onLogin();
    } catch (x) {
      if (signup && /password/i.test(x.message)) setErrors({ password: x.message });
      else setFormErr(x.message);
    } finally { setBusy(false); }
  }

  return (
    <ScrollArea className="h-screen">
    <div className="relative grid min-h-screen place-items-center p-4 text-foreground">
      <GridBackground />
      <ThemeToggle className="absolute top-4 right-4" />
      <Card className="w-full max-w-sm">
        <Form onSubmit={submit} validationErrors={errors} className="grid gap-4">
          <CardHeader>
            <CardTitle className="text-3xl font-semibold tracking-tight" style={{ fontFamily: "'Geist Brand', sans-serif" }}>Reachly</CardTitle>
            <CardDescription>{signup ? 'You are invited. Choose a password to create your account.' : 'Log in to manage your clients.'}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            {inviteState === 'checking' && <p className="text-sm text-muted-foreground">Checking your invite…</p>}
            {inviteState === 'bad' && <div role="alert" className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">This invite link is invalid, already used, or expired. Ask for a new one, or log in below.</div>}
            {formErr && <div role="alert" className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">{formErr}</div>}
            {signup ? (
              <TextField name="email" type="email" fullWidth isReadOnly value={inviteEmail}>
                <Label>Email</Label>
                <Input className={inputClass} autoComplete="email" />
              </TextField>
            ) : (
              <TextField
                name="email" type="email" isRequired autoFocus fullWidth
                validate={(v) => (EMAIL_RE.test(v.trim()) ? null : 'Enter a valid email address.')}
              >
                <Label>Email</Label>
                <Input className={inputClass} placeholder="you@example.com" autoComplete="email" />
                <FieldError />
              </TextField>
            )}
            <TextField
              name="password" type="password" isRequired fullWidth
              validate={(v) => (signup && v.length < 8 ? 'Use at least 8 characters.' : null)}
            >
              <Label>Password</Label>
              <Input className={inputClass} autoComplete={signup ? 'new-password' : 'current-password'} />
              <FieldError />
            </TextField>
            {signup && (
              <TextField name="confirm" type="password" isRequired fullWidth>
                <Label>Confirm password</Label>
                <Input className={inputClass} autoComplete="new-password" />
                <FieldError />
              </TextField>
            )}
          </CardContent>
          <CardFooter className="grid gap-3">
            <Button type="submit" className="w-full" disabled={busy || inviteState === 'checking'}>{signup ? 'Create account' : 'Log in'}</Button>
            {(signup || inviteState === 'bad') ? (
              <p className="text-center text-sm text-muted-foreground">
                Already have an account?{' '}
                <button type="button" onClick={leaveInvite} className="font-medium text-foreground underline-offset-4 hover:underline">Log in</button>
              </p>
            ) : (
              <p className="text-center text-sm text-muted-foreground">Access is by invitation only.</p>
            )}
            {!signup && inviteState !== 'checking' && (
              <Button type="button" variant="outline" className="w-full" onClick={() => { enterGuest(); onGuest(); }}>
                Try it without an account
              </Button>
            )}
          </CardFooter>
        </Form>
      </Card>
    </div>
    </ScrollArea>
  );
}
