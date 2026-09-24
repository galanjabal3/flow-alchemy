import { useState, useEffect, useCallback } from 'react';
import api from '../lib/api';
import { useToast } from '../contexts/ToastContext';
import { ConfirmDialog } from './ConfirmDialog';
import { Key, Plus, Trash2, Shield } from 'lucide-react';

interface Credential {
  id: number;
  name: string;
  credential_type: string;
  created_at: string;
  updated_at: string;
}

export function CredentialsManager() {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newCredential, setNewCredential] = useState({
    name: '',
    credential_type: 'api_key',
    value: '',
  });
  const [creating, setCreating] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Credential | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');
  const { showToast } = useToast();

  useEffect(() => {
    loadCredentials();
  }, []);

  const loadCredentials = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/credentials');
      setCredentials(response.data);
    } catch {
      setError('Failed to load credentials');
    } finally {
      setLoading(false);
    }
  };

  const createCredential = async () => {
    if (!newCredential.name || !newCredential.value) return;
    setCreating(true);
    try {
      await api.post('/credentials', newCredential);
      setNewCredential({ name: '', credential_type: 'api_key', value: '' });
      setShowCreate(false);
      loadCredentials();
      showToast('success', 'Credential created!');
    } catch {
      showToast('error', 'Failed to create credential');
    } finally {
      setCreating(false);
    }
  };

  const confirmDelete = useCallback(async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.delete(`/credentials/${deleteTarget.id}`);
      loadCredentials();
      showToast('success', `"${deleteTarget.name}" deleted`);
    } catch {
      showToast('error', 'Failed to delete credential');
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  }, [deleteTarget, showToast]);

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'api_key': return <Key size={14} />;
      case 'token': return <Shield size={14} />;
      default: return <Key size={14} />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-3 p-8 text-text-muted">
        <div className="w-6 h-6 border-2 border-border border-t-primary rounded-full animate-spin" />
        <span className="text-sm">Loading credentials...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-3 p-4 bg-error-bg border border-error rounded-xl text-error-text">
        <span className="text-sm">{error}</span>
        <button onClick={loadCredentials} className="px-3 py-1 text-sm hover:bg-surface-hover rounded-lg transition-colors">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden animate-fade-in">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield size={16} className="text-primary" />
          <h3 className="font-semibold text-text-primary font-heading">Credentials</h3>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm text-primary hover:bg-primary-bg rounded-lg transition-colors"
        >
          <Plus size={14} />
          Add
        </button>
      </div>

      {showCreate && (
        <div className="p-4 border-b border-border space-y-3 bg-bg animate-slide-up">
          <input
            type="text"
            placeholder="Name"
            value={newCredential.name}
            onChange={(e) => setNewCredential({ ...newCredential, name: e.target.value })}
            className="w-full px-3 py-2.5 bg-surface border border-border rounded-xl text-sm text-text-primary focus:border-primary outline-none transition-all"
          />
          <select
            value={newCredential.credential_type}
            onChange={(e) => setNewCredential({ ...newCredential, credential_type: e.target.value })}
            className="w-full px-3 py-2.5 bg-surface border border-border rounded-xl text-sm text-text-primary focus:border-primary outline-none transition-all"
          >
            <option value="api_key">API Key</option>
            <option value="token">Token</option>
            <option value="password">Password</option>
            <option value="oauth">OAuth</option>
            <option value="basic_auth">Basic Auth</option>
            <option value="custom">Custom</option>
          </select>
          <input
            type="password"
            placeholder="Value"
            value={newCredential.value}
            onChange={(e) => setNewCredential({ ...newCredential, value: e.target.value })}
            className="w-full px-3 py-2.5 bg-surface border border-border rounded-xl text-sm text-text-primary focus:border-primary outline-none transition-all"
          />
          <div className="flex gap-2">
            <button
              onClick={createCredential}
              disabled={creating}
              className="px-3 py-1.5 bg-primary hover:bg-primary-hover text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-colors"
            >
              {creating ? 'Saving...' : 'Save'}
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="px-3 py-1.5 text-sm text-text-secondary hover:bg-surface-hover rounded-xl transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="max-h-64 overflow-y-auto">
        {credentials.length === 0 ? (
          <div className="p-6 text-center text-text-muted animate-fade-in">
            <Key size={28} className="mx-auto mb-2 text-text-muted opacity-50" />
            <p className="text-sm font-medium text-text-secondary mb-1">No credentials stored</p>
            <p className="text-sm">Store API keys, tokens, and secrets securely. They'll be encrypted and available for use in your workflows.</p>
            <p className="text-xs text-text-muted mt-3">Tip: Credentials can be used in HTTP Request nodes for authentication.</p>
          </div>
        ) : (
          credentials.map((cred) => (
            <div key={cred.id} className={`px-4 py-3 border-b border-border last:border-b-0 hover:bg-surface-hover transition-colors flex items-center justify-between border-l-2 ${
              cred.credential_type === 'api_key' ? 'border-l-primary' :
              cred.credential_type === 'token' ? 'border-l-accent' :
              'border-l-border'
            }`}>
              <div className="flex items-center gap-3">
                <span className="text-text-muted">{getTypeIcon(cred.credential_type)}</span>
                <span className="text-sm font-medium text-text-primary">{cred.name}</span>
                <span className="text-xs text-text-muted bg-surface-active px-2 py-0.5 rounded">{cred.credential_type}</span>
              </div>
              <button
                onClick={() => setDeleteTarget(cred)}
                className="p-1.5 text-text-muted hover:text-error hover:bg-error-bg rounded-lg transition-colors"
                title="Delete credential"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))
        )}
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
        title="Delete Credential"
        message={`Delete "${deleteTarget?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        loading={deleting}
      />
    </div>
  );
}
