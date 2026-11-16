import { useState } from 'react';
import { Form, TextField, Label, Input, FieldError } from '@heroui/react';
import { api, setToken } from './api.js';
import { Button } from '@/components/ui/button';
import GridBackground from '@/components/GridBackground';
import ThemeToggle from './ThemeToggle.jsx';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const inputClass = 'blue-glow w-full border border-input shadow-none';

export default function Login({ onLogin }) {
  const [mode, setMode] = useState('login');
  const [errors, setErrors] = useState({});
  const [formErr, setFormErr] = useState('');
  const [busy, setBusy] = useState(false);
  const signup = mode === 'signup';

  function switchMode() {
    setMode(signup ? 'login' : 'signup');
    setErrors({});
    setFormErr('');
  }

  async function submit(e) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.currentTarget));
    const email = String(data.email).trim();
    const password = String(data.password);
    if (signup && password !== data.confirm) {
      setErrors({ confirm: 'Passwords do not match.' });
      return;
    }
    setErrors({});
    setFormErr('');
    setBusy(true);
    try {
      const { access_token } = signup ? await api.signup(email, password) : await api.login(email, password);
      setToken(access_token);
      onLogin();
    } catch (x) {
      // Show account-specific problems under the field they belong to, anything else on top of the form.
      if (signup && /already exists/i.test(x.message)) setErrors({ email: x.message });
      else if (signup && /password/i.test(x.message)) setErrors({ password: x.message });
      else setFormErr(x.message);
    } finally { setBusy(false); }
  }

  return (
    <div className="relative grid min-h-screen place-items-center p-4 text-foreground">
      <GridBackground />
      <ThemeToggle className="absolute top-4 right-4" />
      <Card className="w-full max-w-sm">
        <Form onSubmit={submit} validationErrors={errors} className="grid gap-4">
          <CardHeader>
            <CardTitle className="text-3xl font-semibold tracking-tight" style={{ fontFamily: "'Geist Brand', sans-serif" }}>Reachly</CardTitle>
            <CardDescription>{signup ? 'Create an account to get started.' : 'Log in to manage your clients.'}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            {formErr && <div role="alert" className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">{formErr}</div>}
            <TextField
              name="email" type="email" isRequired autoFocus fullWidth
              validate={(v) => (EMAIL_RE.test(v.trim()) ? null : 'Enter a valid email address.')}
            >
              <Label>Email</Label>
              <Input className={inputClass} placeholder="you@example.com" autoComplete="email" />
              <FieldError />
            </TextField>
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
            <Button type="submit" className="w-full" disabled={busy}>{signup ? 'Sign up' : 'Log in'}</Button>
            <p className="text-center text-sm text-muted-foreground">
              {signup ? 'Already have an account?' : 'No account yet?'}{' '}
              <button type="button" onClick={switchMode} className="font-medium text-foreground underline-offset-4 hover:underline">
                {signup ? 'Log in' : 'Sign up'}
              </button>
            </p>
          </CardFooter>
        </Form>
      </Card>
    </div>
  );
}
