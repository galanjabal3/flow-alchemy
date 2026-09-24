import { useState, useEffect, useCallback } from 'react';
import { createWebhook, listWebhooks, deleteWebhook } from '../lib/api';
import type { WebhookResponse } from '../lib/api';
import { useToast } from '../contexts/ToastContext';
import { ConfirmDialog } from './ConfirmDialog';
import { Link, Plus, Trash2, Loader2, Copy, Check, Eye, EyeOff, Shield } from 'lucide-react';

interface WebhooksPanelProps {
  workflowId: number;
  isActive?: boolean;
}

export function WebhooksPanel({ workflowId, isActive = true }: WebhooksPanelProps) {
  const { showToast } = useToast();
  const [webhooks, setWebhooks] = useState<WebhookResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [newWebhookSecret, setNewWebhookSecret] = useState('');
  const [error, setError] = useState('');
  const [showConfirmDelete, setShowConfirmDelete] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Load webhooks on mount (only when active tab)
  useEffect(() => {
    if (!isActive) return;
    let cancelled = false;
    const doLoad = async () => {
      setLoading(true);
      setError('');
      try {
        const res = await listWebhooks(workflowId);
        if (!cancelled) {
          setWebhooks(res.data);
        }
      } catch {
        if (!cancelled) {
          setError('Failed to load webhooks');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    doLoad();
    return () => { cancelled = true; };
  }, [workflowId, isActive]);

  const handleCreate = async () => {
    setCreating(true);
    setError('');
    try {
      const payload: Record<string, string> = {};
      if (newWebhookSecret && newWebhookSecret.length >= 32) {
        payload.secret = newWebhookSecret;
      }
      const res = await createWebhook(workflowId, payload);
      setWebhooks([...webhooks, res.data]);
      setNewWebhookSecret('');
      setShowCreateForm(false);
      showToast('success', 'Webhook created!');
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to create webhook';
      setError(msg);
      showToast('error', msg);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async () => {
    if (!showConfirmDelete) return;
    setDeleting(true);
    try {
      await deleteWebhook(showConfirmDelete);
      setWebhooks(webhooks.filter((w) => w.webhook_key !== showConfirmDelete));
      setShowConfirmDelete(null);
      showToast('success', 'Webhook deleted');
    } catch {
      showToast('error', 'Failed to delete webhook');
    } finally {
      setDeleting(false);
    }
  };

  // Copy text to clipboard with fallback
  const fallbackCopy = useCallback((text: string) => {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand('copy');
      showToast('success', 'Copied to clipboard');
    } catch {
      showToast('error', 'Failed to copy');
    }
    document.body.removeChild(textarea);
  }, [showToast]);

  const copyToClipboard = useCallback((text: string, label: string) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(() => {
        setCopiedKey(label);
        showToast('success', 'Copied to clipboard');
        setTimeout(() => setCopiedKey(null), 2000);
      }).catch(() => {
        fallbackCopy(text);
      });
    } else {
      fallbackCopy(text);
    }
  }, [showToast, fallbackCopy]);

  // Mask a webhook key for display
  const maskKey = (key: string) => {
    if (key.length <= 8) return '•'.repeat(key.length);
    return `${key.slice(0, 4)}••••••••${key.slice(-4)}`;
  };

  // Check if secret is valid (min 32 chars from backend)
  const canCreate = newWebhookSecret.length === 0 || newWebhookSecret.length >= 32;

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-3 p-8 text-text-muted">
        <div className="w-6 h-6 border-2 border-border border-t-primary rounded-full animate-spin" />
        <span className="text-sm">Loading webhooks...</span>
      </div>
    );
  }

  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Link size={16} className="text-primary" />
          <h3 className="font-semibold text-text-primary font-heading">Webhooks</h3>
          <span className="text-xs text-text-muted bg-surface-active px-2 py-0.5 rounded">
            {webhooks.length}
          </span>
        </div>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm text-primary hover:bg-primary-bg rounded-lg transition-colors"
        >
          <Plus size={14} />
          Add Webhook
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Create Form */}
        {showCreateForm && (
          <div className="p-4 bg-bg border border-border rounded-lg space-y-3 animate-slide-up">
            <label className="text-sm text-text-secondary">
              Secret <span className="text-text-muted">(optional, min 32 characters)</span>
            </label>
            <div className="relative">
              <input
                type={showSecret ? 'text' : 'password'}
                value={newWebhookSecret}
                onChange={(e) => setNewWebhookSecret(e.target.value)}
                placeholder="Enter a secret key (min 32 chars)..."
                className="w-full px-3 py-2.5 bg-surface border border-border rounded-lg text-sm text-text-primary focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all placeholder:text-text-muted pr-10"
              />
              <button
                type="button"
                onClick={() => setShowSecret(!showSecret)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
              >
                {showSecret ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            <p className="text-xs text-text-muted">
              The secret is used to sign webhook payloads. Leave empty if not needed.
            </p>
            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                disabled={creating || !canCreate}
                className="px-3 py-1.5 bg-primary hover:bg-primary-hover text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
              >
                {creating ? <Loader2 size={14} className="animate-spin mx-auto" /> : 'Create'}
              </button>
              <button
                onClick={() => { setShowCreateForm(false); setError(''); }}
                className="px-3 py-1.5 text-sm text-text-secondary hover:bg-surface-hover rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
            {error && (
              <p className="text-xs text-error animate-fade-in">{error}</p>
            )}
            {!canCreate && newWebhookSecret.length > 0 && (
              <p className="text-xs text-error animate-fade-in">Secret must be at least 32 characters</p>
            )}
          </div>
        )}

        {/* Webhook List */}
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {webhooks.length === 0 ? (
            <div className="p-6 text-center bg-bg border border-border rounded-lg animate-fade-in">
              <Link size={28} className="mx-auto mb-2 text-text-muted opacity-50" />
              <p className="text-sm text-text-secondary font-medium">No webhooks configured</p>
              <p className="text-xs text-text-muted mt-1">
                Add a webhook to trigger this workflow via HTTP POST
              </p>
            </div>
          ) : (
            webhooks.map((webhook) => (
              <div
                key={webhook.webhook_key}
                className="bg-bg border border-border rounded-lg p-4 hover:border-border-hover transition-colors"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 space-y-2 min-w-0">
                    {/* Webhook Key */}
                    <div className="flex items-center gap-2">
                      <Shield size={14} className="text-text-muted shrink-0" />
                      <code className="font-mono text-xs text-text-secondary truncate">
                        {maskKey(webhook.webhook_key)}
                      </code>
                      <button
                        onClick={() => copyToClipboard(webhook.webhook_key, `webhook-key-${webhook.webhook_key}`)}
                        className="p-1 text-text-muted hover:text-text-primary rounded transition-colors shrink-0"
                        title="Copy full key"
                      >
                        {copiedKey === `webhook-key-${webhook.webhook_key}` ? (
                          <Check size={12} className="text-success" />
                        ) : (
                          <Copy size={12} />
                        )}
                      </button>
                    </div>

                    {/* Trigger URL */}
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-text-muted shrink-0">URL:</span>
                      <code className="font-mono text-xs text-text-primary bg-surface-hover px-2 py-1 rounded truncate flex-1">
                        {webhook.webhook_url}
                      </code>
                      <button
                        onClick={() => copyToClipboard(webhook.webhook_url, `webhook-url-${webhook.webhook_key}`)}
                        className="p-1 text-text-muted hover:text-text-primary rounded transition-colors shrink-0"
                        title="Copy trigger URL"
                      >
                        {copiedKey === `webhook-url-${webhook.webhook_key}` ? (
                          <Check size={12} className="text-success" />
                        ) : (
                          <Copy size={12} />
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {/* Status indicator */}
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      webhook.is_active
                        ? 'bg-success-bg text-success'
                        : 'bg-surface-active text-text-muted'
                    }`}>
                      {webhook.is_active ? 'Active' : 'Inactive'}
                    </span>

                    {/* Delete button */}
                    <button
                      onClick={() => setShowConfirmDelete(webhook.webhook_key)}
                      disabled={deleting}
                      className="p-1.5 text-text-muted hover:text-error hover:bg-error-bg rounded-lg transition-colors disabled:opacity-50"
                      title="Delete webhook"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="p-3 bg-error-bg border border-error/30 rounded-lg text-sm text-error animate-fade-in">
            {error}
          </div>
        )}

        {/* Info note */}
        <div className="p-3 bg-info-bg border border-info/30 rounded-lg text-xs text-info animate-fade-in">
          <p className="font-medium mb-1">Note:</p>
          <p>Copy the trigger URL to use in your HTTP client. POST to <code className="font-mono">{webhooks[0]?.webhook_url || '...'}</code> to trigger the workflow. If a secret is set, include <code className="font-mono">x-webhook-signature</code> and <code className="font-mono">x-webhook-timestamp</code> headers.</p>
        </div>
      </div>

      <ConfirmDialog
        open={!!showConfirmDelete}
        onClose={() => setShowConfirmDelete(null)}
        onConfirm={handleDelete}
        title="Delete Webhook"
        message="Are you sure you want to delete this webhook? It will no longer be able to trigger this workflow."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="danger"
        loading={deleting}
      />
    </div>
  );
}
