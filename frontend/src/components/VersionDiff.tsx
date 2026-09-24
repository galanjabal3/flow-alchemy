import { useState } from 'react';
import api from '../lib/api';
import { GitCompare, Plus, Minus, ArrowRight } from 'lucide-react';

interface VersionDiffProps {
  workflowId: number;
}

export function VersionDiff({ workflowId }: VersionDiffProps) {
  const [versionA, setVersionA] = useState<number>(1);
  const [versionB, setVersionB] = useState<number>(2);
  const [diff, setDiff] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const compareVersions = async () => {
    if (versionA === versionB) return;
    setLoading(true);
    try {
      const response = await api.get(
        `/workflows/${workflowId}/versions/diff?version_a=${versionA}&version_b=${versionB}`
      );
      setDiff(response.data);
    } catch (error) {
      console.error('Failed to compare versions:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-border flex items-center gap-2">
        <GitCompare size={16} className="text-primary" />
        <h3 className="font-semibold text-text-primary font-heading">Compare Versions</h3>
      </div>

      <div className="p-4 border-b border-border flex items-center gap-3">
        <div className="flex items-center gap-2">
          <label className="text-sm text-text-secondary">From:</label>
          <input
            type="number"
            min="1"
            value={versionA}
            onChange={(e) => setVersionA(parseInt(e.target.value) || 1)}
            className="w-20 px-2 py-1 bg-bg border border-border rounded-lg text-sm text-text-primary focus:border-primary outline-none transition-all"
          />
        </div>
        <ArrowRight size={16} className="text-text-muted" />
        <div className="flex items-center gap-2">
          <label className="text-sm text-text-secondary">To:</label>
          <input
            type="number"
            min="1"
            value={versionB}
            onChange={(e) => setVersionB(parseInt(e.target.value) || 1)}
            className="w-20 px-2 py-1 bg-bg border border-border rounded-lg text-sm text-text-primary focus:border-primary outline-none transition-all"
          />
        </div>
        <button
          onClick={compareVersions}
          disabled={loading}
          className="px-3 py-1.5 bg-primary hover:bg-primary-hover text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
        >
          {loading ? 'Comparing...' : 'Compare'}
        </button>
      </div>

      {diff && (
        <div className="p-4 space-y-4">
          <div>
            <h4 className="text-sm font-medium text-text-secondary mb-2">Added Nodes</h4>
            {diff.added_nodes.length === 0 ? (
              <span className="text-sm text-text-muted">None</span>
            ) : (
              <ul className="space-y-1">
                {diff.added_nodes.map((id: string) => (
                  <li key={id} className="flex items-center gap-2 text-sm text-success-text">
                    <Plus size={12} /> {id}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <h4 className="text-sm font-medium text-text-secondary mb-2">Removed Nodes</h4>
            {diff.removed_nodes.length === 0 ? (
              <span className="text-sm text-text-muted">None</span>
            ) : (
              <ul className="space-y-1">
                {diff.removed_nodes.map((id: string) => (
                  <li key={id} className="flex items-center gap-2 text-sm text-error-text">
                    <Minus size={12} /> {id}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <h4 className="text-sm font-medium text-text-secondary mb-2">Modified Nodes</h4>
            {diff.modified_nodes.length === 0 ? (
              <span className="text-sm text-text-muted">None</span>
            ) : (
              <ul className="space-y-1">
                {diff.modified_nodes.map((id: string) => (
                  <li key={id} className="flex items-center gap-2 text-sm text-accent">
                    <ArrowRight size={12} /> {id}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <h4 className="text-sm font-medium text-text-secondary mb-2">Added Edges</h4>
            {diff.added_edges.length === 0 ? (
              <span className="text-sm text-text-muted">None</span>
            ) : (
              <ul className="space-y-1">
                {diff.added_edges.map((id: string) => (
                  <li key={id} className="flex items-center gap-2 text-sm text-success-text">
                    <Plus size={12} /> {id}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <h4 className="text-sm font-medium text-text-secondary mb-2">Removed Edges</h4>
            {diff.removed_edges.length === 0 ? (
              <span className="text-sm text-text-muted">None</span>
            ) : (
              <ul className="space-y-1">
                {diff.removed_edges.map((id: string) => (
                  <li key={id} className="flex items-center gap-2 text-sm text-error-text">
                    <Minus size={12} /> {id}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
