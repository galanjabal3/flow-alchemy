import { useState, useEffect, useCallback } from 'react';
import api from '../lib/api';
import { Play, SkipForward, Square, Bug, Plus, Minus } from 'lucide-react';

interface DebugState {
  execution_id: string;
  workflow_id: number;
  state: string;
  current_node_index: number;
  total_nodes: number;
  breakpoints: Array<{ node_id: string; enabled: boolean }>;
  node_results: Record<string, any>;
  context: Record<string, any>;
  started_at: string | null;
  paused_at: string | null;
}

interface VisualDebuggerProps {
  executionId: number;
  onDebugComplete?: () => void;
}

export function VisualDebugger({ executionId, onDebugComplete }: VisualDebuggerProps) {
  const [debugState, setDebugState] = useState<DebugState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDebugState = useCallback(async () => {
    try {
      const response = await api.get(`/executions/${executionId}/debug-state`);
      setDebugState(response.data);
    } catch (err) {
      // Debug session might not exist yet
    }
  }, [executionId]);

  useEffect(() => {
    fetchDebugState();
  }, [fetchDebugState]);

  const startDebug = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post(`/executions/${executionId}/debug`, {
        trigger_data: {},
      });
      setDebugState(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start debug session');
    } finally {
      setLoading(false);
    }
  };

  const step = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post(`/executions/${executionId}/step`);
      setDebugState(response.data.state);
      if (response.data.state?.state === 'completed') {
        onDebugComplete?.();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Step failed');
    } finally {
      setLoading(false);
    }
  };

  const resume = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post(`/executions/${executionId}/resume`);
      setDebugState(response.data.state);
      if (response.data.state?.state === 'completed') {
        onDebugComplete?.();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Resume failed');
    } finally {
      setLoading(false);
    }
  };

  const addBreakpoint = async (nodeId: string) => {
    try {
      const response = await api.post(`/executions/${executionId}/breakpoint`, {
        node_id: nodeId,
      });
      setDebugState(response.data.state);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add breakpoint');
    }
  };

  const removeBreakpoint = async (nodeId: string) => {
    try {
      const response = await api.delete(`/executions/${executionId}/breakpoint/${nodeId}`);
      setDebugState(response.data.state);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to remove breakpoint');
    }
  };

  const stopDebug = async () => {
    try {
      await api.delete(`/executions/${executionId}/debug`);
      setDebugState(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to stop debug session');
    }
  };

  const hasBreakpoint = (nodeId: string) => {
    return debugState?.breakpoints.some(bp => bp.node_id === nodeId && bp.enabled) || false;
  };

  if (!debugState) {
    return (
      <div className="bg-surface border border-border rounded-xl overflow-hidden animate-fade-in">
        <div className="px-4 py-3 border-b border-border flex items-center gap-2">
          <Bug size={16} className="text-primary" />
          <h3 className="font-semibold text-text-primary font-heading">Visual Debugger</h3>
        </div>
        <div className="p-4 text-center">
          <p className="text-sm text-text-muted mb-2">Step through your workflow execution node by node. Set breakpoints to pause at specific nodes and inspect outputs in real-time.</p>
          <p className="text-xs text-text-muted mb-4">Tip: Use 'Step' to go one node at a time, or 'Resume' to run until the next breakpoint.</p>
          <button
            onClick={startDebug}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-primary hover:bg-primary-hover text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-all duration-200"
          >
            {loading ? (
              <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Play size={14} />
            )}
            {loading ? 'Starting...' : 'Start Debug'}
          </button>
        </div>
        {error && (
          <div className="px-4 py-3 bg-error-bg border-t border-error text-error-text text-sm">
            {error}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden animate-fade-in">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bug size={16} className="text-primary" />
          <h3 className="font-semibold text-text-primary font-heading">Visual Debugger</h3>
        </div>
        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
          debugState.state === 'completed' ? 'bg-success-bg text-success-text' :
          debugState.state === 'running' ? 'bg-accent-bg text-accent' :
          debugState.state === 'paused' ? 'bg-warning-bg text-warning-text' :
          'bg-surface-hover text-text-muted'
        }`}>
          {debugState.state}
        </span>
      </div>

      <div className="px-4 py-3 border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-text-muted">
            {debugState.current_node_index} / {debugState.total_nodes} nodes
          </span>
        </div>
        <div className="w-full h-2 bg-bg rounded-full overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-500 ease-out"
            style={{ width: `${(debugState.current_node_index / debugState.total_nodes) * 100}%` }}
          />
        </div>
      </div>

      <div className="px-4 py-3 border-b border-border flex gap-2">
        {debugState.state === 'idle' && (
          <button
            onClick={startDebug}
            disabled={loading}
            className="inline-flex items-center gap-1 px-3 py-1.5 bg-success hover:bg-success/90 text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-colors"
          >
            <Play size={14} />
            Start
          </button>
        )}
        {(debugState.state === 'running' || debugState.state === 'paused') && (
          <>
            <button
              onClick={step}
              disabled={loading}
              className="inline-flex items-center gap-1 px-3 py-1.5 bg-accent hover:bg-accent/90 text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-colors"
            >
              <SkipForward size={14} />
              Step
            </button>
            <button
              onClick={resume}
              disabled={loading}
              className="inline-flex items-center gap-1 px-3 py-1.5 bg-primary hover:bg-primary-hover text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-colors"
            >
              <Play size={14} />
              Resume
            </button>
          </>
        )}
        <button
          onClick={stopDebug}
          disabled={loading}
          className="inline-flex items-center gap-1 px-3 py-1.5 bg-error hover:bg-error/90 text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-colors"
        >
          <Square size={14} />
          Stop
        </button>
      </div>

      {error && (
        <div className="px-4 py-3 bg-error-bg border-t border-error text-error-text text-sm">
          {error}
        </div>
      )}

      <div className="p-4">
        <h4 className="text-sm font-medium text-text-secondary mb-3">Node Results</h4>
        <div className="space-y-2">
          {Object.entries(debugState.node_results).map(([nodeId, result], index) => (
            <div
              key={nodeId}
              className={`p-3 bg-bg border rounded-lg animate-fade-in ${
                result.status === 'completed' ? 'border-success' :
                result.status === 'running' ? 'border-accent' :
                result.status === 'failed' ? 'border-error' :
                'border-border'
              }`}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-text-muted">{nodeId}</span>
                  <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                    result.status === 'completed' ? 'bg-success-bg text-success-text' :
                    result.status === 'running' ? 'bg-accent-bg text-accent' :
                    result.status === 'failed' ? 'bg-error-bg text-error-text' :
                    'bg-surface-hover text-text-muted'
                  }`}>
                    {result.status}
                  </span>
                </div>
                <button
                  className={`p-1 rounded-lg transition-colors ${
                    hasBreakpoint(nodeId)
                      ? 'bg-error text-white'
                      : 'text-text-muted hover:bg-surface-hover'
                  }`}
                  onClick={() =>
                    hasBreakpoint(nodeId) ? removeBreakpoint(nodeId) : addBreakpoint(nodeId)
                  }
                  title={hasBreakpoint(nodeId) ? 'Remove breakpoint' : 'Add breakpoint'}
                >
                  {hasBreakpoint(nodeId) ? <Minus size={12} /> : <Plus size={12} />}
                </button>
              </div>
              {result.output && (
                <pre className="text-xs text-text-secondary overflow-x-auto font-mono bg-surface p-2 rounded">
                  {JSON.stringify(result.output, null, 2)}
                </pre>
              )}
              {result.error && (
                <pre className="text-xs text-error-text overflow-x-auto font-mono bg-error-bg p-2 rounded mt-2">
                  {result.error}
                </pre>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
