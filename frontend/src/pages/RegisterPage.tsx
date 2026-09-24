import { useState, useMemo, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Copy, Check, Eye, EyeOff, ArrowRight, ArrowLeft, KeyRound } from 'lucide-react';

export function RegisterPage() {
  useEffect(() => { document.title = 'Create Account — FlowAlchemy'; }, []);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [step, setStep] = useState<'form' | 'success'>('form');
  const { register } = useAuth();
  const navigate = useNavigate();

  const passwordValidation = useMemo(() => {
    if (!password) return null;
    const errors: string[] = [];
    if (password.length < 8) errors.push('at least 8 characters');
    if (!/[A-Z]/.test(password)) errors.push('an uppercase letter');
    if (!/[a-z]/.test(password)) errors.push('a lowercase letter');
    if (!/[0-9]/.test(password)) errors.push('a number');
    return errors.length > 0 ? errors : null;
  }, [password]);

  const isFormValid = useMemo(() => {
    return (
      email.trim() !== '' &&
      password.length >= 8 &&
      passwordValidation === null
    );
  }, [email, password, passwordValidation]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (passwordValidation && passwordValidation.length > 0) {
      setError(`Password must contain ${passwordValidation.join(', ')}`);
      return;
    }

    setIsLoading(true);

    try {
      const { api_key } = await register(email, password);
      setApiKey(api_key);
      setStep('success');
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'object' && detail.errors) {
        setError(detail.errors.join('. '));
      } else {
        setError(detail || 'Registration failed');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const copyApiKey = async () => {
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(apiKey);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = apiKey;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // silently fail
    }
  };

  if (step === 'success') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg p-4">
        <div className="w-full max-w-md animate-scale-in">
          <div className="bg-surface border border-border rounded-2xl p-8 shadow-lg">
            <div className="text-center mb-8">
              <div className="w-14 h-14 bg-success/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Check size={28} className="text-success" />
              </div>
              <h1 className="text-2xl font-bold text-text-primary font-heading">
                Account Created!
              </h1>
              <p className="text-text-muted mt-2">Your API key has been generated</p>
            </div>

            <div className="p-4 bg-accent/10 border border-accent/30 rounded-xl mb-6">
              <div className="flex items-start gap-3">
                <KeyRound size={18} className="text-accent mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary mb-2">Your API Key</p>
                  <div className="flex items-center gap-2 p-2.5 bg-bg border border-border rounded-lg">
                    <code className="flex-1 font-mono text-xs text-primary break-all leading-relaxed">
                      {showKey ? apiKey : '••••••••••••••••••••••••••••••••'}
                    </code>
                    {apiKey && (
                      <>
                        <button
                          onClick={() => setShowKey(!showKey)}
                          className="p-1.5 border border-border rounded-lg hover:bg-surface-hover hover:text-text-primary transition-colors shrink-0"
                          title={showKey ? 'Hide' : 'Reveal'}
                        >
                          {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
                        </button>
                        <button
                          onClick={copyApiKey}
                          className="p-1.5 border border-border rounded-lg hover:bg-surface-hover hover:text-text-primary transition-colors shrink-0"
                        >
                          {copied ? <Check size={14} className="text-success" /> : <Copy size={14} />}
                        </button>
                      </>
                    )}
                  </div>
                  <p className="mt-2 text-xs text-accent font-medium">
                    Save this key now — it won't be shown again.
                  </p>
                </div>
              </div>
            </div>

            <button
              onClick={() => navigate('/login')}
              className="w-full py-3 px-4 bg-primary hover:bg-primary-hover text-white font-semibold rounded-xl transition-all duration-200 flex items-center justify-center gap-2 group"
            >
              Continue to Sign In
              <ArrowRight
                size={16}
                className="group-hover:translate-x-1 transition-transform"
              />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg p-4">
      <div className="w-full max-w-md animate-fade-in">
        {/* Back to home */}
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors mb-6"
        >
          <ArrowLeft size={14} />
          Back to home
        </Link>

        {/* Logo */}
        <div className="text-center mb-8">
          <img src="/logo.svg" alt="FlowAlchemy" className="w-12 h-12 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-text-primary font-heading">FlowAlchemy</h1>
          <p className="text-text-muted mt-2">Create your account</p>
        </div>

        {/* Card */}
        <div className="bg-surface border border-border rounded-2xl p-8 shadow-lg">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-text-primary">Get started</h2>
            <p className="text-sm text-text-muted mt-1">Create a free account to start building</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 bg-error-bg border border-error/50 rounded-xl text-error-text text-sm animate-shake">
                {error}
              </div>
            )}

            <div className="space-y-2">
              <label htmlFor="email" className="block text-sm font-medium text-text-secondary">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="w-full px-4 py-3 bg-bg border border-border rounded-xl text-text-primary placeholder:text-text-muted focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all duration-200"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="password" className="block text-sm font-medium text-text-secondary">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Create a password"
                required
                className="w-full px-4 py-3 bg-bg border border-border rounded-xl text-text-primary placeholder:text-text-muted focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all duration-200"
              />
              {password && passwordValidation && (
                <ul className="text-xs space-y-0.5">
                  {passwordValidation.map((rule) => (
                    <li key={rule} className="text-error-text">
                      Needs {rule}
                    </li>
                  ))}
                </ul>
              )}
              {password && !passwordValidation && (
                <p className="text-xs text-success-text">Password looks good</p>
              )}
            </div>

            <div className="space-y-2">
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-text-secondary">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm your password"
                required
                className="w-full px-4 py-3 bg-bg border border-border rounded-xl text-text-primary placeholder:text-text-muted focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all duration-200"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading || !isFormValid}
              className="w-full py-3 px-4 bg-primary hover:bg-primary-hover text-white font-semibold rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2 group"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Create Account
                  <ArrowRight
                    size={16}
                    className="group-hover:translate-x-1 transition-transform"
                  />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center mt-6 text-text-muted text-sm">
          Already have an account?{' '}
          <Link
            to="/login"
            className="text-primary hover:text-primary-hover font-medium transition-colors"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
