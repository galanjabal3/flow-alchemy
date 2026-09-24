import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ReactFlowProvider } from '@xyflow/react';
import api from '../lib/api';
import { WorkflowEditor } from '../components/WorkflowEditor';
import { ExecutionHistory } from '../components/ExecutionHistory';
import { VersionHistory } from '../components/VersionHistory';
import { CredentialsManager } from '../components/CredentialsManager';
import { VisualDebugger } from '../components/VisualDebugger';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { SchedulerPanel } from '../components/SchedulerPanel';
import { WebhooksPanel } from '../components/WebhooksPanel';
import { ArrowLeft, Code2, History, GitBranch, Key, Bug, Clock, Link2 } from 'lucide-react';

type Tab = 'editor' | 'history' | 'versions' | 'credentials' | 'debug' | 'schedule' | 'webhooks';

export function WorkflowPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [workflow, setWorkflow] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<Tab>('editor');
  const [debugExecutionId, setDebugExecutionId] = useState<number | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [pendingTarget, setPendingTarget] = useState<string | null>(null);
  const [showUnsavedConfirm, setShowUnsavedConfirm] = useState(false);

  const handleNavigation = useCallback((target: string) => {
    if (isDirty) {
      setPendingTarget(target);
      setShowUnsavedConfirm(true);
      return;
    }
    navigate(target);
  }, [navigate, isDirty]);

  const confirmNavigation = useCallback(() => {
    setShowUnsavedConfirm(false);
    const target = pendingTarget;
    setPendingTarget(null);
    if (target) {
      navigate(target);
    }
  }, [navigate, pendingTarget]);

  const cancelNavigation = useCallback(() => {
    setShowUnsavedConfirm(false);
    setPendingTarget(null);
  }, []);

  const onDirtyChange = useCallback((dirty: boolean) => {
    setIsDirty(dirty);
  }, []);

  const handleDebugExecution = useCallback((executionId: number) => {
    setDebugExecutionId(executionId);
    setActiveTab('debug');
  }, []);

  useEffect(() => {
    if (!id) return;
    api.get(`/workflows/${id}`)
      .then((res) => {
        setWorkflow(res.data);
        document.title = `${res.data.name} — FlowAlchemy`;
      })
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load workflow'))
      .finally(() => setIsLoading(false));
  }, [id]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-bg">
        <div className="w-10 h-10 border-[3px] border-border border-t-primary rounded-full animate-spin" />
        <p className="text-text-muted">Loading workflow...</p>
      </div>
    );
  }

  if (error || !workflow) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-bg">
        <p className="text-text-muted">{error || 'Workflow not found'}</p>
        <button
          onClick={() => navigate('/dashboard')}
          className="mt-4 px-4 py-2 bg-primary hover:bg-primary-hover text-white font-medium rounded-lg transition-colors"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  const tabs: { id: Tab; label: string; icon: typeof Code2 }[] = [
    { id: 'editor', label: 'Editor', icon: Code2 },
    { id: 'history', label: 'History', icon: History },
    { id: 'versions', label: 'Versions', icon: GitBranch },
    { id: 'credentials', label: 'Credentials', icon: Key },
    ...(workflow.id ? [{ id: 'schedule' as Tab, label: 'Schedule', icon: Clock }, { id: 'webhooks' as Tab, label: 'Webhooks', icon: Link2 }] : []),
    ...(debugExecutionId ? [{ id: 'debug' as Tab, label: 'Debug', icon: Bug }] : []),
  ];

  return (
    <div className="h-screen flex flex-col bg-bg overflow-hidden">
      <header className="px-6 py-3 bg-surface border-b border-border relative z-30">
        <div className="flex items-center gap-2 mb-1">
          <button
            onClick={() => handleNavigation('/dashboard')}
            className="p-1.5 text-text-muted hover:text-text-primary hover:bg-surface-hover rounded-lg transition-colors"
            title="Back to dashboard"
          >
            <ArrowLeft size={16} />
          </button>
          <nav className="flex items-center gap-1.5 text-sm">
            <button onClick={() => handleNavigation('/dashboard')} className="text-text-muted hover:text-primary transition-colors">Workflows</button>
            <span className="text-text-muted">/</span>
            <span className="font-semibold text-text-primary font-heading">{workflow.name}</span>
          </nav>
        </div>
        <p className="text-sm text-text-muted ml-9">{workflow.description || 'No description'}</p>
      </header>

      <div className="flex gap-1 px-6 pt-2 bg-surface border-b border-border overflow-x-auto scrollbar-none relative z-30">
        {tabs.map(({ id: tabId, label, icon: Icon }) => (
          <button
            key={tabId}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-t-lg transition-all duration-200 whitespace-nowrap ${
              activeTab === tabId
                ? 'bg-bg text-primary border-b-2 border-primary'
                : 'text-text-muted hover:text-text-primary hover:bg-surface-hover'
            }`}
            onClick={() => setActiveTab(tabId)}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      <main className="flex-1 overflow-hidden relative">
        <div className={`absolute inset-0 ${activeTab === 'editor' ? '' : 'hidden'}`}>
          <ReactFlowProvider>
            <WorkflowEditor workflow={workflow} onDirtyChange={onDirtyChange} />
          </ReactFlowProvider>
        </div>
        <div className={`absolute inset-0 overflow-y-auto ${activeTab === 'history' ? '' : 'hidden'}`}>
          <ExecutionHistory workflowId={workflow.id} onDebugExecution={handleDebugExecution} />
        </div>
        <div className={`absolute inset-0 overflow-y-auto p-6 ${activeTab === 'versions' ? '' : 'hidden'}`}>
          <VersionHistory workflowId={workflow.id} />
        </div>
        <div className={`absolute inset-0 overflow-y-auto p-6 ${activeTab === 'credentials' ? '' : 'hidden'}`}>
          <CredentialsManager />
        </div>
        {/* Schedule Panel */}
        <div className={`absolute inset-0 overflow-y-auto p-6 ${activeTab === 'schedule' ? '' : 'hidden'}`}>
          <SchedulerPanel workflowId={workflow.id} isTabActive={activeTab === 'schedule'} />
        </div>
        {/* Webhooks Panel */}
        <div className={`absolute inset-0 overflow-y-auto p-6 ${activeTab === 'webhooks' ? '' : 'hidden'}`}>
          <WebhooksPanel workflowId={workflow.id} isActive={activeTab === 'webhooks'} />
        </div>
        <div className={`absolute inset-0 overflow-y-auto p-6 ${activeTab === 'debug' ? '' : 'hidden'}`}>
          {debugExecutionId && (
            <VisualDebugger
              executionId={debugExecutionId}
              onDebugComplete={() => setDebugExecutionId(null)}
            />
          )}
        </div>
      </main>

      <ConfirmDialog
        open={showUnsavedConfirm}
        onClose={cancelNavigation}
        onConfirm={confirmNavigation}
        title="Unsaved Changes"
        message="You have unsaved changes. Leave this page anyway?"
        confirmLabel="Leave"
        cancelLabel="Stay"
        variant="warning"
      />
    </div>
  );
}
