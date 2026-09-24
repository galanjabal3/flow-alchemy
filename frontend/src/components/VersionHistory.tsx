import { useState, useEffect, useCallback } from 'react';
import api from '../lib/api';
import { formatDate } from '../lib/formatDate';
import { useToast } from '../contexts/ToastContext';
import { ConfirmDialog } from './ConfirmDialog';
import { VersionDiff } from './VersionDiff';
import { Clock, RotateCcw, GitBranch, Plus, GitCompare } from 'lucide-react';

interface WorkflowVersion {
  id: number;
  workflow_id: number;
  version: number;
  definition: any;
  change_summary: string | null;
  created_by: number;
  created_at: string;
}

interface VersionHistoryProps {
  workflowId: number;
  onRollback?: (version: number) => void;
}

export function VersionHistory({ workflowId, onRollback }: VersionHistoryProps) {
  const [versions, setVersions] = useState<WorkflowVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [summary, setSummary] = useState('');
  const [rollbackTarget, setRollbackTarget] = useState<WorkflowVersion | null>(null);
  const [rollingBack, setRollingBack] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const [error, setError] = useState('');
  const { showToast } = useToast();

  useEffect(() => {
    loadVersions();
  }, [workflowId]);

  const loadVersions = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get(`/workflows/${workflowId}/versions`);
      setVersions(response.data);
    } catch {
      setError('Failed to load versions');
    } finally {
      setLoading(false);
    }
  };

  const createVersion = async () => {
    setCreating(true);
    try {
      await api.post(`/workflows/${workflowId}/versions`, {
        change_summary: summary || null,
      });
      setSummary('');
      loadVersions();
      showToast('success', 'Version saved!');
    } catch {
      showToast('error', 'Failed to save version');
    } finally {
      setCreating(false);
    }
  };

  const handleRollback = async (version: number) => {
    try {
      await api.post(`/workflows/${workflowId}/versions/${version}/rollback`);
      loadVersions();
      onRollback?.(version);
      showToast('success', `Rolled back to v${version}`);
    } catch {
      showToast('error', 'Failed to rollback');
    }
  };

  const confirmRollback = useCallback(async () => {
    if (!rollbackTarget) return;
    setRollingBack(true);
    await handleRollback(rollbackTarget.version);
    setRollingBack(false);
    setRollbackTarget(null);
  }, [rollbackTarget]);

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-3 p-8 text-text-muted">
        <div className="w-6 h-6 border-2 border-border border-t-primary rounded-full animate-spin" />
        <span className="text-sm">Loading versions...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-3 p-4 bg-error-bg border border-error rounded-xl text-error-text">
        <span className="text-sm">{error}</span>
        <button onClick={loadVersions} className="px-3 py-1 text-sm hover:bg-surface-hover rounded-lg transition-colors">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden animate-fade-in">
      <div className="px-4 py-3 border-b border-border flex items-center gap-2">
        <GitBranch size={16} className="text-primary" />
        <h3 className="font-semibold text-text-primary font-heading">Version History</h3>
      </div>

      <div className="p-4 border-b border-border flex gap-2">
        <input
          type="text"
          placeholder="Change summary (optional)"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          className="flex-1 px-3 py-2.5 bg-bg border border-border rounded-xl text-sm text-text-primary placeholder:text-text-muted focus:border-primary focus:ring-2 focus:ring-primary-bg outline-none transition-all"
        />
        <button
          onClick={createVersion}
          disabled={creating}
          className="inline-flex items-center gap-1 px-3 py-2.5 bg-primary hover:bg-primary-hover text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-all duration-200"
        >
          {creating ? (
            <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <Plus size={14} />
          )}
          {creating ? 'Saving...' : 'Save Version'}
        </button>
        {versions.length >= 2 && (
          <button
            onClick={() => setShowDiff(!showDiff)}
            className={`inline-flex items-center gap-1 px-3 py-2.5 text-sm font-medium rounded-xl transition-all duration-200 ${
              showDiff
                ? 'bg-accent text-white'
                : 'bg-surface-hover text-text-secondary hover:text-text-primary'
            }`}
          >
            <GitCompare size={14} />
            {showDiff ? 'Hide Diff' : 'Compare'}
          </button>
        )}
      </div>

      <div className="max-h-64 overflow-y-auto">
        {versions.length === 0 ? (
          <div className="p-6 text-center text-text-muted animate-fade-in">
            <GitBranch size={28} className="mx-auto mb-2 text-text-muted opacity-50" />
            <p className="text-sm font-medium text-text-secondary mb-1">No versions saved</p>
            <p className="text-sm">Save a version to track changes to your workflow. You can rollback to any previous version.</p>
            <p className="text-xs text-text-muted mt-3">Tip: Add a change summary when saving to remember what you changed.</p>
          </div>
        ) : (
          versions.map((version) => (
            <div key={version.id} className={`px-4 py-3 border-b border-border last:border-b-0 hover:bg-surface-hover transition-colors ${version.version === versions[0]?.version ? 'border-l-2 border-l-primary' : 'border-l-2 border-l-border'}`}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 text-xs font-medium bg-primary-bg text-primary rounded">v{version.version}</span>
                  <span className="flex items-center gap-1 text-xs text-text-muted">
                    <Clock size={12} />
                    {formatDate(version.created_at)}
                  </span>
                </div>
                <button
                  className="inline-flex items-center gap-1 px-2 py-1 text-xs text-text-muted hover:text-text-primary hover:bg-surface-active rounded-lg transition-all duration-200"
                  onClick={() => setRollbackTarget(version)}
                  title={`Rollback to version ${version.version}`}
                >
                  <RotateCcw size={14} />
                  Rollback
                </button>
              </div>
              {version.change_summary && (
                <div className="text-sm text-text-secondary">{version.change_summary}</div>
              )}
            </div>
          ))
        )}
      </div>

      {showDiff && (
        <div className="p-4 border-t border-border">
          <VersionDiff workflowId={workflowId} />
        </div>
      )}

      <ConfirmDialog
        open={!!rollbackTarget}
        onClose={() => setRollbackTarget(null)}
        onConfirm={confirmRollback}
        title="Rollback Version"
        message={`Rollback to v${rollbackTarget?.version}? The current workflow definition will be replaced.`}
        confirmLabel="Rollback"
        variant="warning"
        loading={rollingBack}
      />
    </div>
  );
}
