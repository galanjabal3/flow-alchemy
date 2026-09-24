import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { formatMonthYear } from '../lib/formatDate';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import {
  ArrowLeft,
  User,
  Key,
  Palette,
  Save,
  Loader2,
  Eye,
  EyeOff,
  Copy,
  Check,
  RefreshCw,
} from 'lucide-react';

type Tab = 'profile' | 'preferences' | 'api-keys';

const THEME_KEY = 'flowalchemy-theme';
const AUTOSAVE_KEY = 'flowalchemy-autosave';

export function SettingsPage() {
  useEffect(() => { document.title = 'Settings — FlowAlchemy'; }, []);
  const navigate = useNavigate();
  const { user } = useAuth();
  const { showToast } = useToast();
  const [activeTab, setActiveTab] = useState<Tab>('profile');

  // Profile
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPw, setShowCurrentPw] = useState(false);
  const [showNewPw, setShowNewPw] = useState(false);
  const [showConfirmPw, setShowConfirmPw] = useState(false);
  const [pwMsg, setPwMsg] = useState('');
  const [pwErr, setPwErr] = useState('');
  const [savingPw, setSavingPw] = useState(false);

  // Preferences
  const [autoSave, setAutoSave] = useState(() => {
    return localStorage.getItem(AUTOSAVE_KEY) !== 'false';
  });
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem(THEME_KEY) as 'dark' | 'light') || 'dark';
  });

  // API Keys
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [newKeyAlert, setNewKeyAlert] = useState(false);

  const handleChangePassword = async () => {
    setSavingPw(true);
    setPwMsg('');
    setPwErr('');
    if (newPassword !== confirmPassword) {
      setPwErr('Passwords do not match');
      setSavingPw(false);
      return;
    }
    try {
      await api.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPwMsg('Password changed');
      showToast('success', 'Password changed!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setPwMsg(''), 3000);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to change password';
      setPwErr(msg);
      showToast('error', msg);
    } finally {
      setSavingPw(false);
    }
  };

  const handleThemeChange = (newTheme: 'dark' | 'light') => {
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem(THEME_KEY, newTheme);
  };

  const handleRegenerateKey = async () => {
    setRegenerating(true);
    try {
      const res = await api.post('/auth/regenerate-api-key');
      setApiKey(res.data.api_key);
      setShowKey(true);
      setNewKeyAlert(true);
      showToast('success', 'API key regenerated!');
      setTimeout(() => setNewKeyAlert(false), 8000);
    } catch {
      showToast('error', 'Failed to regenerate API key');
    } finally {
      setRegenerating(false);
    }
  };

  const copyKey = async () => {
    if (apiKey && navigator.clipboard) {
      await navigator.clipboard.writeText(apiKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const tabs: { id: Tab; label: string; icon: typeof User }[] = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'preferences', label: 'Preferences', icon: Palette },
    { id: 'api-keys', label: 'API Keys', icon: Key },
  ];

  return (
    <div className="h-screen flex flex-col bg-bg overflow-hidden">
      {/* Header */}
      <header className="px-6 py-3 bg-surface border-b border-border flex items-center gap-4 shrink-0">
        <button
          onClick={() => navigate('/dashboard')}
          className="p-2 text-text-muted hover:text-text-primary hover:bg-surface-hover rounded-lg transition-colors"
          title="Back to Dashboard"
        >
          <ArrowLeft size={18} />
        </button>
        <h1 className="text-lg font-bold font-heading text-text-primary">Settings</h1>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar tabs */}
        <aside className="w-56 bg-surface border-r border-border p-4 flex flex-col gap-1 shrink-0">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === id
                  ? 'bg-primary/10 text-primary'
                  : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </aside>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-2xl">
            {/* Profile Tab */}
            {activeTab === 'profile' && (
              <div className="space-y-8 animate-fade-in">
                <div>
                  <h2 className="text-xl font-bold text-text-primary font-heading mb-1">Profile</h2>
                  <p className="text-sm text-text-muted">Manage your account settings</p>
                </div>

                {/* Email - read only */}
                <div className="bg-surface border border-border rounded-xl p-6 space-y-4">
                  <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                    <User size={16} className="text-primary" />
                    Email
                  </h3>
                  <input
                    type="email"
                    value={user?.email || ''}
                    disabled
                    className="w-full px-4 py-2.5 bg-bg/50 border border-border rounded-lg text-text-muted cursor-not-allowed"
                  />
                  <p className="text-xs text-text-muted">Contact support to change your email address.</p>
                </div>

                {/* Password */}
                <div className="bg-surface border border-border rounded-xl p-6 space-y-4">
                  <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                    <Key size={16} className="text-primary" />
                    Change Password
                  </h3>
                  <div className="relative">
                    <input
                      type={showCurrentPw ? 'text' : 'password'}
                      placeholder="Current password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      className="w-full px-4 py-2.5 bg-bg border border-border rounded-lg text-text-primary placeholder-text-muted focus:border-primary focus:ring-1 focus:ring-primary outline-none pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowCurrentPw(!showCurrentPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
                    >
                      {showCurrentPw ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  <div className="relative">
                    <input
                      type={showNewPw ? 'text' : 'password'}
                      placeholder="New password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full px-4 py-2.5 bg-bg border border-border rounded-lg text-text-primary placeholder-text-muted focus:border-primary focus:ring-1 focus:ring-primary outline-none pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPw(!showNewPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
                    >
                      {showNewPw ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  <div className="relative">
                    <input
                      type={showConfirmPw ? 'text' : 'password'}
                      placeholder="Confirm new password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="w-full px-4 py-2.5 bg-bg border border-border rounded-lg text-text-primary placeholder-text-muted focus:border-primary focus:ring-1 focus:ring-primary outline-none pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPw(!showConfirmPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
                    >
                      {showConfirmPw ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {pwMsg && (
                    <p className="text-sm text-success animate-fade-in">{pwMsg}</p>
                  )}
                  {pwErr && (
                    <p className="text-sm text-error animate-fade-in">{pwErr}</p>
                  )}
                  <button
                    onClick={handleChangePassword}
                    disabled={savingPw || !currentPassword || !newPassword || !confirmPassword}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-40 transition-colors"
                  >
                    {savingPw ? <Loader2 size={14} className="animate-spin" /> : <Key size={14} />}
                    Change Password
                  </button>
                </div>

                {/* Account info */}
                <div className="bg-surface border border-border rounded-xl p-6 space-y-3">
                  <h3 className="text-sm font-semibold text-text-primary">Account Info</h3>
                  <div className="flex justify-between text-sm">
                    <span className="text-text-muted">Plan</span>
                    <span className="text-text-primary font-medium capitalize">{user?.plan}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-text-muted">Member since</span>
                    <span className="text-text-primary font-medium">
                      {(user as any)?.created_at
                        ? formatMonthYear((user as any).created_at)
                        : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Preferences Tab */}
            {activeTab === 'preferences' && (
              <div className="space-y-8 animate-fade-in">
                <div>
                  <h2 className="text-xl font-bold text-text-primary font-heading mb-1">Preferences</h2>
                  <p className="text-sm text-text-muted">Customize your workspace</p>
                </div>

                {/* Theme */}
                <div className="bg-surface border border-border rounded-xl p-6 space-y-4">
                  <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                    <Palette size={16} className="text-primary" />
                    Theme
                  </h3>
                  <div className="flex gap-3">
                    <button
                      onClick={() => handleThemeChange('dark')}
                      className={`flex-1 px-4 py-3 rounded-lg border text-sm font-medium transition-all ${
                        theme === 'dark'
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-border bg-bg text-text-secondary hover:border-primary/50'
                      }`}
                    >
                      🌙 Dark
                    </button>
                    <button
                      onClick={() => handleThemeChange('light')}
                      className={`flex-1 px-4 py-3 rounded-lg border text-sm font-medium transition-all ${
                        theme === 'light'
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-border bg-bg text-text-secondary hover:border-primary/50'
                      }`}
                    >
                      ☀️ Light
                    </button>
                  </div>
                </div>

                {/* Auto-save */}
                <div className="bg-surface border border-border rounded-xl p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 mr-4">
                      <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                        <Save size={16} className="text-primary" />
                        Auto-save
                      </h3>
                      <p className="text-xs text-text-muted mt-1">Automatically save workflow changes</p>
                    </div>
                    <button
                      role="switch"
                      aria-checked={autoSave}
                      aria-label="Toggle auto-save"
                      onClick={() => {
                        const next = !autoSave;
                        setAutoSave(next);
                        localStorage.setItem(AUTOSAVE_KEY, next.toString());
                      }}
                      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface ${
                        autoSave ? 'bg-primary' : 'bg-border'
                      }`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-lg ring-0 transition-transform duration-200 ease-in-out ${
                          autoSave ? 'translate-x-[22px]' : 'translate-x-[3px]'
                        }`}
                      />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* API Keys Tab */}
            {activeTab === 'api-keys' && (
              <div className="space-y-8 animate-fade-in">
                <div>
                  <h2 className="text-xl font-bold text-text-primary font-heading mb-1">API Keys</h2>
                  <p className="text-sm text-text-muted">Manage your API access</p>
                </div>

                <div className="bg-surface border border-border rounded-xl p-6 space-y-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Key size={16} className="text-primary" />
                    <h3 className="text-sm font-semibold text-text-primary">Your API Key</h3>
                  </div>

                  <p className="text-xs text-text-muted">
                    Use this key to authenticate API requests. Keep it secret — do not share it publicly.
                  </p>

                  <div className="flex items-center gap-2">
                    <div className="flex-1 px-4 py-2.5 bg-bg border border-border rounded-lg font-mono text-sm text-text-primary truncate">
                      {showKey && apiKey ? apiKey : '••••••••••••••••••••••••••••••••'}
                    </div>
                    {apiKey && (
                      <>
                        <button
                          onClick={() => setShowKey(!showKey)}
                          className="p-2.5 text-text-muted hover:text-text-primary hover:bg-surface-hover rounded-lg transition-colors"
                          title={showKey ? 'Hide' : 'Reveal'}
                        >
                          {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                        <button
                          onClick={copyKey}
                          className="p-2.5 text-text-muted hover:text-text-primary hover:bg-surface-hover rounded-lg transition-colors"
                          title="Copy"
                        >
                          {copied ? <Check size={16} className="text-success" /> : <Copy size={16} />}
                        </button>
                      </>
                    )}
                  </div>

                  {newKeyAlert && (
                    <div className="p-3 bg-warning/10 border border-warning/30 rounded-lg text-sm text-warning animate-fade-in">
                      ⚠️ Save this key now. It will not be shown again after you leave this page.
                    </div>
                  )}

                  <button
                    onClick={handleRegenerateKey}
                    disabled={regenerating}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-surface-hover border border-border text-text-primary rounded-lg text-sm font-medium hover:border-primary hover:text-primary disabled:opacity-40 transition-colors"
                  >
                    {regenerating ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <RefreshCw size={14} />
                    )}
                    Regenerate API Key
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
