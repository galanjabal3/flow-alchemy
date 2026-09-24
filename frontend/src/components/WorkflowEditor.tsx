import { useCallback, useEffect, useLayoutEffect, useRef, useState, useMemo } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  BackgroundVariant,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  useReactFlow,
} from '@xyflow/react';
import type { Node, Edge, Connection, NodeChange, EdgeChange } from '@xyflow/react';
import type { OnNodeDrag } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import '../react-flow-overrides.css';
import api from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { useExecutionWebSocket } from '../lib/useExecutionWebSocket';
import { NodePalette } from './NodePalette';
import { NodeConfigForm } from './NodeConfigForm';
import { CustomNode } from './CustomNode';
import { useUndoRedo } from '../hooks/useUndoRedo';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { PanelLeftClose, Undo2, Redo2, Menu } from 'lucide-react';

interface WorkflowData {
  id: number;
  name: string;
  description: string | null;
  definition: { nodes: Node[]; edges: Edge[] } | null;
}

interface WorkflowEditorProps {
  workflow?: WorkflowData;
  onDirtyChange?: (dirty: boolean) => void;
}

export function WorkflowEditor({ workflow, onDirtyChange }: WorkflowEditorProps) {
  const { token } = useAuth();
  const { screenToFlowPosition } = useReactFlow();
  const { showToast } = useToast();

  // ── State ──
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const nodesRef = useRef<Node[]>([]);
  const edgesRef = useRef<Edge[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const selectedNode = useMemo(() => nodes.find((n) => n.id === selectedNodeId) || null, [nodes, selectedNodeId]);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [isDirty, setIsDirty] = useState(false);
  const saveStatus: 'saved' | 'saving' | 'unsaved' = isSaving ? 'saving' : isDirty ? 'unsaved' : 'saved';
  const [showPalette, setShowPalette] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState<any>(null);
  const [runError, setRunError] = useState('');
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(() => {
    return localStorage.getItem('flowalchemy-autosave') !== 'false';
  });
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [nodeStatuses, setNodeStatuses] = useState<Record<string, string>>({});
  const [credentials, setCredentials] = useState<Array<{ id: number; name: string; credential_type: string }>>([]);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const workflowIdRef = useRef<number | null>(null);

  // ── Responsive ──
  const isMobile = useMediaQuery('(max-width: 767px)');
  const isTablet = useMediaQuery('(min-width: 768px) and (max-width: 1023px)');
  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);
  const [configOpen, setConfigOpen] = useState(true);

  const undoRedo = useUndoRedo();

  // Keep refs in sync
  useEffect(() => { nodesRef.current = nodes; }, [nodes]);
  useEffect(() => { edgesRef.current = edges; }, [edges]);

  // ── WebSocket ──
  const { isConnected } = useExecutionWebSocket({
    executionId,
    token: token || '',
    onStatusChange: (status) => {
      if (status === 'completed' || status === 'failed') {
        setIsRunning(false);
        if (executionId) {
          api.get(`/workflows/${workflowIdRef.current}/executions`).then((res) => {
            const execution = res.data.find((e: any) => e.id.toString() === executionId);
            if (execution) {
              setRunResult(execution);
            }
          });
        }
      }
    },
    onNodeUpdate: (nodeId, status) => {
      setNodeStatuses((prev) => ({ ...prev, [nodeId]: status }));
    },
  });

  // ── Load workflow ──
  useEffect(() => {
    if (workflow?.id) {
      workflowIdRef.current = workflow.id;
    }
  }, [workflow?.id]);

  useLayoutEffect(() => {
    if (workflow?.definition) {
      const def = workflow.definition;
      if (def.nodes) setNodes(def.nodes);
      if (def.edges) setEdges(def.edges);
      undoRedo.reset();
    }
  }, [workflow, undoRedo]);

  useEffect(() => {
    api.get('/credentials')
      .then((res) => setCredentials(res.data))
      .catch(() => {
        showToast('error', 'Failed to load credentials. Please refresh the page.');
      });
  }, [showToast]);

  // ── ReactFlow callbacks ──
  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((nds) => {
      const newNodes = applyNodeChanges(changes, nds);
      const hasDataChange = changes.some((c) => c.type !== 'select' && c.type !== 'position');
      if (hasDataChange) {
        undoRedo.pushSnapshot(newNodes, edgesRef.current);
      }
      return newNodes;
    });
    const hasDataChange = changes.some((c) => c.type !== 'select');
    if (hasDataChange) setIsDirty(true);
  }, [undoRedo]);

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setEdges((eds) => {
      const newEdges = applyEdgeChanges(changes, eds);
      const hasDataChange = changes.some((c) => c.type !== 'select');
      if (hasDataChange) {
        undoRedo.pushSnapshot(nodesRef.current, newEdges);
      }
      return newEdges;
    });
    const hasDataChange = changes.some((c) => c.type !== 'select');
    if (hasDataChange) setIsDirty(true);
  }, [undoRedo]);

  const onConnect = useCallback((connection: Connection) => {
    setEdges((eds) => {
      const newEdges = addEdge(connection, eds);
      undoRedo.pushSnapshot(nodesRef.current, newEdges);
      return newEdges;
    });
    setIsDirty(true);
  }, [undoRedo]);

  const onNodeDragStop: OnNodeDrag<Node> = useCallback((_event, _node) => {
    undoRedo.pushSnapshot(nodesRef.current, edgesRef.current);
  }, [undoRedo]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
    if (isMobile && !configOpen) setConfigOpen(true);
  }, [isMobile, configOpen]);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  // ── Custom node operations (with snapshot) ──
  const addNode = useCallback((nodeType: string, label: string, inputSchema?: any, position?: { x: number; y: number }) => {
    const newNode: Node = {
      id: crypto.randomUUID(),
      type: 'custom',
      data: { label, nodeType, config: {}, inputSchema },
      position: position || { x: 250, y: 0 },
    };
    setNodes((nds) => {
      if (!position) {
        const y = nds.length * 100 + 50;
        newNode.position = { x: 250, y };
      }
      undoRedo.pushSnapshot([...nds, newNode], edgesRef.current);
      return [...nds, newNode];
    });
    setIsDirty(true);
  }, [undoRedo]);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    const nodeType = event.dataTransfer.getData('application/reactflow-type');
    const label = event.dataTransfer.getData('application/reactflow-label');
    const schemaStr = event.dataTransfer.getData('application/reactflow-schema');

    if (!nodeType || !label) return;

    const position = screenToFlowPosition({
      x: event.clientX,
      y: event.clientY,
    });

    let schema;
    try {
      schema = JSON.parse(schemaStr);
    } catch {
      schema = undefined;
    }

    addNode(nodeType, label, schema, position);
  }, [screenToFlowPosition, addNode]);

  const deleteNode = useCallback((nodeId: string) => {
    setNodes((nds) => {
      const newNodes = nds.filter((n) => n.id !== nodeId);
      undoRedo.pushSnapshot(newNodes, edgesRef.current.filter((e) => e.source !== nodeId && e.target !== nodeId));
      return newNodes;
    });
    setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
    setSelectedNodeId(null);
    setIsDirty(true);
  }, [undoRedo]);

  const updateNodeLabel = useCallback((nodeId: string, label: string) => {
    setNodes((nds) => {
      const newNodes = nds.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, label } } : n));
      undoRedo.pushSnapshot(newNodes, edgesRef.current);
      return newNodes;
    });
    setIsDirty(true);
  }, [undoRedo]);

  const updateNodeConfig = useCallback((nodeId: string, config: Record<string, any>) => {
    setNodes((nds) => {
      const newNodes = nds.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, config } } : n));
      undoRedo.pushSnapshot(newNodes, edgesRef.current);
      return newNodes;
    });
    setIsDirty(true);
  }, [undoRedo]);

  // ── Undo / Redo handlers ──
  const handleUndo = useCallback(() => {
    const snapshot = undoRedo.undo();
    if (snapshot) {
      setNodes(snapshot.nodes);
      setEdges(snapshot.edges);
      setIsDirty(true);
    }
  }, [undoRedo]);

  const handleRedo = useCallback(() => {
    const snapshot = undoRedo.redo();
    if (snapshot) {
      setNodes(snapshot.nodes);
      setEdges(snapshot.edges);
      setIsDirty(true);
    }
  }, [undoRedo]);

  // ── Keyboard shortcuts ──
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') return;

      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z' && !e.shiftKey) {
        e.preventDefault();
        handleUndo();
      }
      if ((e.metaKey || e.ctrlKey) && ((e.shiftKey && e.key.toLowerCase() === 'z') || e.key.toLowerCase() === 'y')) {
        e.preventDefault();
        handleRedo();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleUndo, handleRedo]);

  // ── Save & auto-save ──
  const saveWorkflow = useCallback(async () => {
    if (!workflowIdRef.current) return;
    setIsSaving(true);
    setSaveError('');
    try {
      await api.put(`/workflows/${workflowIdRef.current}`, {
        definition: { nodes: nodesRef.current, edges: edgesRef.current },
      });
      setIsDirty(false);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to save';
      setSaveError(msg);
      showToast('error', msg);
    } finally {
      setIsSaving(false);
    }
  }, [showToast]);

  useEffect(() => {
    onDirtyChange?.(isDirty);
  }, [isDirty, onDirtyChange]);

  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === 'flowalchemy-autosave') {
        setAutoSaveEnabled(e.newValue !== 'false');
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  useEffect(() => {
    if (autoSaveEnabled && isDirty && workflowIdRef.current && !isSaving) {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      saveTimerRef.current = setTimeout(() => {
        saveWorkflow();
      }, 1500);
    }
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, [autoSaveEnabled, isDirty, isSaving, saveWorkflow]);

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [isDirty]);

  // ── Run workflow ──
  const runWorkflow = useCallback(async () => {
    if (!workflowIdRef.current || isRunning) return;
    setIsRunning(true);
    setRunError('');
    setRunResult(null);
    setNodeStatuses({});
    try {
      const res = await api.post(`/workflows/${workflowIdRef.current}/run`, {
        input_data: {},
      });
      const execId = res.data.id.toString();
      setExecutionId(execId);
      setRunResult(res.data);

      for (let i = 0; i < 30; i++) {
        await new Promise((r) => setTimeout(r, 1000));
        try {
          const poll = await api.get(`/workflows/${workflowIdRef.current}/executions`);
          const exec = poll.data.find((e: any) => e.id.toString() === execId);
          if (exec && (exec.status === 'completed' || exec.status === 'failed')) {
            setRunResult(exec);
            setIsRunning(false);
            return;
          }
        } catch {
          // ignore polling errors
        }
      }
      setIsRunning(false);
    } catch (err: any) {
      setRunError(err.response?.data?.detail || 'Run failed');
      setIsRunning(false);
    }
  }, [isRunning]);

  // ── Node types ──
  const nodeTypes = useMemo(() => ({
    custom: CustomNode,
    trigger: CustomNode,
    http_request: CustomNode,
    transform: CustomNode,
    condition: CustomNode,
    delay: CustomNode,
    output: CustomNode,
  }), []);

  return (
    <div className="flex h-full bg-bg relative">
      {/* Shared mobile backdrop (z-10 so WorkflowPage header z-30 stays above) */}
      {isMobile && (sidebarOpen || configOpen) && (
        <div
          className="fixed inset-0 bg-black/40 z-10"
          onClick={() => { setSidebarOpen(false); setConfigOpen(false); }}
        />
      )}

        {/* Palette sidebar */}
        <div
          className={`flex flex-col h-full overflow-hidden transition-width duration-200 shrink-0 ${
            isMobile
              ? (sidebarOpen ? 'fixed left-0 top-0 bottom-0 z-20 translate-x-0' : '-translate-x-full')
              : ''
          }`}
        >
          <NodePalette className={isTablet ? 'w-48' : undefined} isMobile={isMobile} onNodeClick={addNode} />
      </div>

       <div className="flex-1 flex flex-col relative min-w-0 z-20">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 bg-surface border-b border-border">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowPalette(!showPalette)}
              className="p-1.5 text-text-muted hover:text-text-primary hover:bg-surface-hover rounded-lg transition-colors"
              title={showPalette ? 'Hide node panel' : 'Show node panel'}
            >
              <PanelLeftClose size={16} className={!showPalette ? 'rotate-180' : ''} />
            </button>
            {isMobile && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-1.5 text-text-muted hover:text-text-primary hover:bg-surface-hover rounded-lg transition-colors"
                title="Show nodes"
              >
                <Menu size={16} />
              </button>
            )}
            <span className="text-sm text-text-muted">
              {nodes.length} node{nodes.length !== 1 ? 's' : ''} • {edges.length} edge{edges.length !== 1 ? 's' : ''}
            </span>
            <span className={`text-sm ${saveStatus === 'saved' ? 'text-success' : saveStatus === 'saving' ? 'text-accent' : 'text-warning'}`}>
              {saveStatus === 'saved' && 'Saved'}
              {saveStatus === 'saving' && 'Saving...'}
              {saveStatus === 'unsaved' && 'Unsaved changes'}
            </span>
            {saveError && <span className="text-sm text-error-text">{saveError}</span>}
          </div>
          <div className="flex items-center gap-2">
            {/* Undo / Redo buttons */}
            <button
              onClick={handleUndo}
              disabled={!undoRedo.canUndo}
              className="p-1.5 text-text-muted hover:text-text-primary hover:bg-surface-hover rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title="Undo (Ctrl+Z)"
            >
              <Undo2 size={16} />
            </button>
            <button
              onClick={handleRedo}
              disabled={!undoRedo.canRedo}
              className="p-1.5 text-text-muted hover:text-text-primary hover:bg-surface-hover rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title="Redo (Ctrl+Shift+Z)"
            >
              <Redo2 size={16} />
            </button>
            <button
              onClick={saveWorkflow}
              disabled={isSaving || !isDirty}
              className="px-3 py-1.5 text-sm text-text-secondary hover:bg-surface-hover rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Save
            </button>
            <button
              onClick={runWorkflow}
              disabled={isRunning || nodes.length === 0}
              className="px-4 py-1.5 text-sm bg-success hover:bg-success/90 text-white font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isRunning ? 'Running...' : 'Run'}
            </button>
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1 h-full w-full">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeDragStop={onNodeDragStop}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onDragOver={onDragOver}
            onDrop={onDrop}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Controls
              showInteractive={false}
              className="!bg-surface !border-border !shadow-md [&>button]:!bg-surface [&>button]:!border-border [&>button]:!text-text-primary [&>button]:hover:!bg-surface-hover [&>button]:!border-0 [&>button:not(:last-child)]:!border-b [&>button:not(:last-child)]:!border-border"
            />
            <Background variant={BackgroundVariant.Dots} gap={16} />
            {nodes.length === 0 && (
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none animate-fade-in">
                <p className="text-text-muted text-center max-w-xs">
                  Start building your workflow
                </p>
                <p className="text-text-muted text-sm text-center max-w-xs mt-1">
                  Drag nodes from the left panel and connect them to create automation flows.
                </p>
              </div>
            )}
          </ReactFlow>
        </div>

        {/* Run Result Panel */}
        {(isRunning || runResult || runError) && (
          <div className="absolute bottom-0 left-0 right-0 bg-surface border-t border-border shadow-lg max-h-[40%] overflow-y-auto animate-slide-up">
            <div className="flex items-center justify-between px-4 py-2 border-b border-border">
              <h4 className="font-semibold text-text-primary font-heading">Execution Result</h4>
              <div className="flex items-center gap-2">
                {isConnected && <span className="text-success" title="Realtime connected">●</span>}
                <button
                  onClick={() => { setRunResult(null); setRunError(''); setExecutionId(null); setNodeStatuses({}); }}
                  className="text-text-muted hover:text-text-primary text-xl leading-none"
                >
                  ×
                </button>
              </div>
            </div>

            {isRunning && (
              <div className="flex items-center gap-3 p-4 text-text-muted">
                <div className="w-5 h-5 border-2 border-border border-t-primary rounded-full animate-spin" />
                <span>
                  {runResult?.status === 'queued' && 'Queued...'}
                  {runResult?.status === 'running' && 'Running workflow...'}
                  {!runResult?.status && 'Starting...'}
                </span>
              </div>
            )}

            {Object.keys(nodeStatuses).length > 0 && (
              <div className="px-4 py-2 border-t border-border space-y-1">
                {Object.entries(nodeStatuses).map(([nodeId, status]) => (
                  <div key={nodeId} className="flex items-center gap-2 text-sm">
                    <span className={`w-2 h-2 rounded-full ${
                      status === 'completed' ? 'bg-success' :
                      status === 'running' ? 'bg-accent' :
                      status === 'failed' ? 'bg-error' :
                      'bg-text-muted'
                    }`} />
                    <span className="text-text-muted font-mono text-xs">{nodeId.slice(0, 8)}...</span>
                    <span className="text-text-secondary">{status}</span>
                  </div>
                ))}
              </div>
            )}

            {runError && (
              <div className="px-4 py-3 bg-error-bg border-t border-error text-error-text text-sm">
                <span className="font-semibold">Error:</span> {typeof runError === 'string' ? runError : JSON.stringify(runError)}
              </div>
            )}

            {runResult && (
              <div className="p-4 space-y-3">
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                    runResult.status === 'completed' ? 'bg-success-bg text-success-text' :
                    runResult.status === 'failed' ? 'bg-error-bg text-error-text' :
                    'bg-surface-hover text-text-muted'
                  }`}>
                    {runResult.status}
                  </span>
                  <span className="text-sm text-text-muted">
                    {runResult.completed_at && runResult.started_at
                      ? `${((new Date(runResult.completed_at).getTime() - new Date(runResult.started_at).getTime()) / 1000).toFixed(1)}s`
                      : '—'}
                  </span>
                </div>
                {runResult.output_data && (
                  <div>
                    <label className="block text-xs font-medium text-text-secondary mb-1">Output</label>
                    <pre className="p-3 bg-bg border border-border rounded-lg text-sm text-text-primary overflow-x-auto font-mono">
                      {JSON.stringify(runResult.output_data, null, 2)}
                    </pre>
                  </div>
                )}
                {runResult.error_log && (
                  <div>
                    <label className="block text-xs font-medium text-error-text mb-1">Error Log</label>
                    <pre className="p-3 bg-error-bg border border-error rounded-lg text-sm text-error-text overflow-x-auto font-mono">
                      {runResult.error_log}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Mobile config panel overlay */}
      {isMobile && configOpen && (
        <button
          onClick={() => setConfigOpen(false)}
          className="fixed right-3 top-16 z-30 p-2 bg-surface border border-border rounded-lg shadow-md text-text-primary hover:bg-surface-hover transition-colors"
          title="Close properties"
        >
          <span className="text-lg leading-none">×</span>
        </button>
      )}

      {/* Node Properties Panel */}
      {selectedNode && (
        <aside
          className={`bg-surface border-l border-border flex flex-col overflow-hidden transition-width duration-200 shrink-0 ${
            isMobile
              ? (configOpen ? 'fixed right-0 top-0 bottom-0 z-30 w-72 translate-x-0' : 'w-0 -translate-x-full border-l-0')
              : 'w-72'
          }`}
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
            <h3 className="font-semibold text-text-primary font-heading">Node Properties</h3>
            <div className="flex items-center gap-2">
              {isMobile && (
                <button
                  onClick={() => setConfigOpen(false)}
                  className="p-1 text-text-muted hover:text-text-primary rounded transition-colors"
                  title="Close"
                >
                  <span className="text-lg leading-none">×</span>
                </button>
              )}
              <button
                onClick={() => deleteNode(selectedNode.id)}
                className="px-3 py-1 text-sm text-error hover:bg-error-bg rounded-lg transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <div className="space-y-1">
              <label className="block text-sm font-medium text-text-secondary">Label</label>
              <input
                type="text"
                value={selectedNode.data.label as string}
                onChange={(e) => updateNodeLabel(selectedNode.id, e.target.value)}
                className="w-full px-3 py-2 bg-bg border border-border rounded-lg text-text-primary focus:border-primary focus:ring-2 focus:ring-primary-bg outline-none transition-all"
              />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium text-text-secondary">Type</label>
              <input
                type="text"
                value={selectedNode.data.nodeType as string || 'default'}
                disabled
                className="w-full px-3 py-2 bg-bg border border-border rounded-lg text-text-muted cursor-not-allowed"
              />
            </div>
            {selectedNode && (
              <NodeConfigForm
                nodeType={selectedNode.data.nodeType as string}
                inputSchema={selectedNode.data.inputSchema as any || { properties: {} }}
                config={(selectedNode.data.config as Record<string, any>) || {}}
                onChange={(config) => updateNodeConfig(selectedNode.id, config)}
                credentials={credentials}
              />
            )}
          </div>
        </aside>
      )}
    </div>
  );
}
