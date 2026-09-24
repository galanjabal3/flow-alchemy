import { useCallback, useEffect, useState } from 'react';
import { Clock, Bug, ChevronDown, Loader2 } from 'lucide-react';
import api from '../lib/api';
import { fetchExecutionNodes } from '../lib/api';
import type { ExecutionNode } from '../lib/api';
import { formatShortDateTime } from '../lib/formatDate';

interface Execution {
  id: number;
  workflow_id: number;
  status: string;
  trigger: string;
  input_data: Record<string, any> | null;
  output_data: Record<string, any> | null;
  error_log: string | null;
  started_at: string;
  completed_at: string | null;
}

interface ExecutionHistoryProps {
  workflowId: number;
  onDebugExecution?: (executionId: number) => void;
}

function formatDuration(started: string, completed: string | null): string {
  if (!completed) return '—';
  const ms = new Date(completed).getTime() - new Date(started).getTime();
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatNodeDuration(durationMs: number | null): string {
  if (!durationMs) return '—';
  return `${durationMs}ms`;
}

function getNodeStatusStyles(status: ExecutionNode['status']) {
  switch (status) {
    case 'completed':
      return { badge: 'bg-success-bg text-success-text', dot: 'bg-success' };
    case 'failed':
      return { badge: 'bg-error-bg text-error-text', dot: 'bg-error' };
    case 'running':
      return { badge: 'bg-accent-bg text-accent', dot: 'bg-accent' };
    case 'skipped':
      return { badge: 'bg-warning-bg text-warning-text', dot: 'bg-warning' };
    case 'pending':
      return { badge: 'bg-surface-hover text-text-muted', dot: 'bg-text-muted' };
    default:
      return { badge: 'bg-surface-hover text-text-muted', dot: 'bg-text-muted' };
  }
}

export function ExecutionHistory({ workflowId, onDebugExecution }: ExecutionHistoryProps) {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [nodesExpandedId, setNodesExpandedId] = useState<number | null>(null);
  const [nodesData, setNodesData] = useState<Record<number, ExecutionNode[]>>({});
  const [nodesLoading, setNodesLoading] = useState<Record<number, boolean>>({});
  const [nodesError, setNodesError] = useState<Record<number, string>>({});

  const fetchExecutions = useCallback(async () => {
    setIsLoading(true);
    setError('');
    try {
      const res = await api.get(`/workflows/${workflowId}/executions`, {
        params: { limit: 20 },
      });
      setExecutions(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load executions');
    } finally {
      setIsLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    fetchExecutions();
  }, [fetchExecutions]);

  const handleToggleNodes = useCallback(async (executionId: number) => {
    if (nodesExpandedId === executionId) {
      setNodesExpandedId(null);
      return;
    }
    setNodesExpandedId(executionId);
    if (nodesData[executionId]) return; // already loaded
    setNodesLoading((prev) => ({ ...prev, [executionId]: true }));
    setNodesError((prev) => ({ ...prev, [executionId]: '' }));
    try {
      const nodes = await fetchExecutionNodes(executionId);
      setNodesData((prev) => ({ ...prev, [executionId]: nodes }));
    } catch (err: any) {
      setNodesError((prev) => ({ ...prev, [executionId]: err.response?.data?.detail || 'Failed to load nodes' }));
    } finally {
      setNodesLoading((prev) => ({ ...prev, [executionId]: false }));
    }
  }, [nodesExpandedId, nodesData]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-3 p-8 text-text-muted">
        <div className="w-8 h-8 border-2 border-border border-t-primary rounded-full animate-spin" />
        <span className="text-sm">Loading executions...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-3 p-4 bg-error-bg border border-error rounded-xl text-error-text">
        <span>{error}</span>
        <button onClick={fetchExecutions} className="px-3 py-1 text-sm hover:bg-surface-hover rounded-lg transition-colors">
          Retry
        </button>
      </div>
    );
  }

  if (executions.length === 0) {
    return (
      <div className="p-8 text-center text-text-muted animate-fade-in">
        <Clock size={32} className="mx-auto mb-3 text-text-muted opacity-50" />
        <p className="text-sm font-medium text-text-secondary mb-1">No executions yet</p>
        <p className="text-sm">Run your workflow to see execution history here. Each run will show status, duration, and output.</p>
        <p className="text-xs text-text-muted mt-3">Tip: Click 'Run' in the editor toolbar to execute your workflow.</p>
      </div>
    );
  }

  return (
    <div className="bg-bg animate-fade-in">
      <div className="grid grid-cols-[100px_1fr_80px_120px_80px] gap-4 px-4 py-2 bg-surface border-b border-border text-xs font-medium text-text-muted uppercase sticky top-0 z-10">
        <span>Status</span>
        <span>Trigger</span>
        <span>Duration</span>
        <span>Started</span>
        <span>Actions</span>
      </div>
      {executions.map((ex) => {
        const nodeStatusStyles = getNodeStatusStyles(ex.status as ExecutionNode['status']);
        return (
          <div
            key={ex.id}
            className={`border-b border-border hover:bg-surface-hover transition-colors ${expandedId === ex.id ? 'bg-surface' : ''}`}
          >
            <div
              className="grid grid-cols-[100px_1fr_80px_120px_80px] gap-4 px-4 py-3 items-center"
              onClick={() => setExpandedId(expandedId === ex.id ? null : ex.id)}
            >
              <span>
                <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium rounded-full ${nodeStatusStyles.badge}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${nodeStatusStyles.dot}`} />
                  {ex.status}
                </span>
              </span>
              <span className="text-sm text-text-secondary">{ex.trigger}</span>
              <span className="text-sm text-text-muted">{formatDuration(ex.started_at, ex.completed_at)}</span>
              <span className="text-sm text-text-muted">{formatShortDateTime(ex.started_at)}</span>
              <span className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                <button
                  onClick={() => handleToggleNodes(ex.id)}
                  className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-surface-active rounded-md transition-colors"
                >
                  {nodesLoading[ex.id] ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : (
                    <ChevronDown size={12} className={nodesExpandedId === ex.id ? 'rotate-180' : ''} />
                  )}
                  Detail
                </button>
              </span>
            </div>
            {expandedId === ex.id && (
              <div className="px-4 pb-4 space-y-3 animate-scale-in">
                {onDebugExecution && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onDebugExecution(ex.id); }}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-accent hover:bg-accent/90 text-white text-xs font-medium rounded-lg transition-colors"
                  >
                    <Bug size={12} />
                    Debug Execution
                  </button>
                )}
                {ex.output_data && (
                  <div>
                    <label className="block text-xs font-medium text-text-secondary mb-1">Output</label>
                    <pre className="p-3 bg-bg border border-border rounded-lg text-sm text-text-primary overflow-x-auto font-mono">
                      {JSON.stringify(ex.output_data, null, 2)}
                    </pre>
                  </div>
                )}
                {ex.error_log && (
                  <div>
                    <label className="block text-xs font-medium text-error-text mb-1">Error</label>
                    <pre className="p-3 bg-error-bg border border-error rounded-lg text-sm text-error-text overflow-x-auto font-mono">
                      {ex.error_log}
                    </pre>
                  </div>
                )}
                {!ex.output_data && !ex.error_log && (
                  <div className="text-sm text-text-muted">No output data</div>
                )}
              </div>
            )}
            {/* Node Detail Section */}
            {nodesExpandedId === ex.id && (
              <div className="px-4 pb-4 space-y-2 animate-scale-in" onClick={(e) => e.stopPropagation()}>
                <label className="block text-xs font-medium text-text-secondary mb-2">Node Execution Details</label>
                {nodesLoading[ex.id] && (
                  <div className="flex items-center gap-2 text-text-muted text-sm">
                    <Loader2 size={14} className="animate-spin" />
                    Loading nodes...
                  </div>
                )}
                {nodesError[ex.id] && (
                  <div className="text-error-text text-xs bg-error-bg border border-error rounded-lg px-3 py-2">{nodesError[ex.id]}</div>
                )}
                {nodesData[ex.id] && (
                  <div className="space-y-2">
                    {nodesData[ex.id].map((node) => {
                      const ns = getNodeStatusStyles(node.status);
                      return (
                        <div
                          key={node.id}
                          className="p-3 bg-surface border border-border rounded-lg hover:border-border-hover transition-colors"
                        >
                          <div className="flex items-center gap-2 mb-2">
                            <span className={`w-2 h-2 rounded-full ${ns.dot}`} />
                            <span className="text-xs font-mono font-medium text-text-primary">{node.node_ref}</span>
                            <span className="text-xs text-text-muted">·</span>
                            <span className="text-xs text-text-secondary">{node.node_type}</span>
                            <span className={`ml-auto inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${ns.badge}`}>
                              <span className={`w-1.5 h-1.5 rounded-full ${ns.dot}`} />
                              {node.status}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 text-xs text-text-muted">
                            <span>Duration: {formatNodeDuration(node.duration_ms)}</span>
                            {node.started_at && <span>Started: {formatShortDateTime(node.started_at)}</span>}
                            {node.completed_at && <span>Completed: {formatShortDateTime(node.completed_at)}</span>}
                          </div>
                          {node.error_log && (
                            <div className="mt-2">
                              <label className="text-xs font-medium text-error-text">Error Log</label>
                              <pre className="mt-1 p-2 bg-error-bg border border-error/30 rounded-lg text-xs text-error-text overflow-x-auto font-mono max-h-32 overflow-y-auto">
                                {node.error_log}
                              </pre>
                            </div>
                          )}
                          {node.output_data && (
                            <div className="mt-2">
                              <label className="text-xs font-medium text-text-secondary">Output</label>
                              <pre className="mt-1 p-2 bg-bg border border-border rounded-lg text-xs font-mono text-text-primary overflow-x-auto max-h-40 overflow-y-auto">
                                {JSON.stringify(node.output_data, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}