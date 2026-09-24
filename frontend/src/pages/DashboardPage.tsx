import { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { formatDate } from '../lib/formatDate';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { Modal } from '../components/Modal';
import { ConfirmDialog } from '../components/ConfirmDialog';
import {
  Plus,
  Trash2,
  Settings,
  LogOut,
  Search,
  Workflow,
  Zap,
  Clock,
  ArrowRight,
  ChevronDown,
} from 'lucide-react';

interface WorkflowType {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

interface Execution {
  id: number;
  status: string;
  started_at: string;
  completed_at: string | null;
}

type SortKey = 'updated_at' | 'created_at' | 'name';
type SortOrder = 'asc' | 'desc';

export function DashboardPage() {
  useEffect(() => { document.title = 'Dashboard — FlowAlchemy'; }, []);
  const [workflows, setWorkflows] = useState<WorkflowType[]>([]);
  const [recentExecutions, setRecentExecutions] = useState<Execution[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();

  // Create modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWorkflowName, setNewWorkflowName] = useState('');
  const [newWorkflowDesc, setNewWorkflowDesc] = useState('');

  // Delete confirm
  const [deleteTarget, setDeleteTarget] = useState<WorkflowType | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Search + sort
  const [searchQuery, setSearchQuery] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('updated_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [showAll, setShowAll] = useState(false);

  // User menu dropdown
  const [showUserMenu, setShowUserMenu] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchData();
  }, []);

  // Close user menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const closeCreateModal = useCallback(() => {
    setShowCreateModal(false);
    setNewWorkflowName('');
    setNewWorkflowDesc('');
  }, []);

  const fetchData = async () => {
    setError('');
    try {
      const wfRes = await api.get('/workflows/');
      setWorkflows(wfRes.data);

      if (wfRes.data.length > 0) {
        try {
          const execResults = await Promise.all(
            wfRes.data.map((wf: WorkflowType) =>
              api.get(`/workflows/${wf.id}/executions`, { params: { limit: 100 } })
                .then((res) => res.data)
                .catch(() => [])
            )
          );
          setRecentExecutions(execResults.flat());
        } catch {}
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load data');
    } finally {
      setIsLoading(false);
    }
  };

  const createWorkflow = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const res = await api.post('/workflows/', {
        name: newWorkflowName,
        description: newWorkflowDesc || null,
        definition: { nodes: [], edges: [] },
      });
      setWorkflows([res.data, ...workflows]);
      closeCreateModal();
      showToast('success', 'Workflow created!');
      navigate(`/workflow/${res.data.id}`);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to create workflow';
      setError(msg);
      showToast('error', msg);
    }
  };

  const confirmDelete = useCallback(async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.delete(`/workflows/${deleteTarget.id}`);
      setWorkflows((prev) => prev.filter((w) => w.id !== deleteTarget.id));
      showToast('success', `"${deleteTarget.name}" deleted`);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to delete workflow';
      setError(msg);
      showToast('error', msg);
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  }, [deleteTarget, showToast]);

  const filteredWorkflows = useMemo(() => {
    let result = [...workflows];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (w) =>
          w.name.toLowerCase().includes(q) ||
          (w.description && w.description.toLowerCase().includes(q))
      );
    }

    result.sort((a, b) => {
      let cmp = 0;
      if (sortKey === 'name') cmp = a.name.localeCompare(b.name);
      else if (sortKey === 'updated_at')
        cmp = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime();
      else cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      return sortOrder === 'asc' ? cmp : -cmp;
    });

    return result;
  }, [workflows, searchQuery, sortKey, sortOrder]);

  const displayWorkflows = showAll ? filteredWorkflows : filteredWorkflows.slice(0, 6);

  const activeWorkflows = workflows.filter((w) => w.is_active).length;

  return (
    <div className="h-screen flex flex-col bg-bg overflow-hidden">
      {/* Header */}
      <header className="px-6 py-3 bg-surface border-b border-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <img src="/logo.svg" alt="FlowAlchemy" className="w-8 h-8" />
          <h1 className="text-xl font-bold font-heading text-primary">FlowAlchemy</h1>
        </div>

        {/* User menu */}
        <div className="relative" ref={userMenuRef}>
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-surface-hover transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center text-sm font-bold">
              {user?.email?.charAt(0).toUpperCase() || '?'}
            </div>
            <ChevronDown size={14} className={`text-text-muted transition-transform ${showUserMenu ? 'rotate-180' : ''}`} />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-56 bg-surface border border-border rounded-xl shadow-xl py-1 z-50 animate-scale-in">
              <div className="px-4 py-2.5 border-b border-border">
                <p className="text-sm font-medium text-text-primary truncate">{user?.email}</p>
                <p className="text-xs text-text-muted capitalize">{user?.plan} plan</p>
              </div>
              <button
                onClick={() => { setShowUserMenu(false); navigate('/settings'); }}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-colors"
              >
                <Settings size={16} />
                Settings
              </button>
              <button
                onClick={() => { setShowUserMenu(false); logout(); }}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-text-secondary hover:text-error hover:bg-error-bg transition-colors"
              >
                <LogOut size={16} />
                Logout
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="flex-1 overflow-y-auto">
        {/* Hero Section */}
        <div className="px-6 pt-8 pb-6 bg-gradient-to-br from-primary/5 via-transparent to-accent/5">
          <div className="max-w-5xl mx-auto">
            <h2 className="text-2xl font-bold text-text-primary font-heading mb-1">
              Welcome back{user?.email ? `, ${user.email.split('@')[0]}` : ''}
            </h2>
            <p className="text-text-muted mb-6">
              Manage and automate your workflows
            </p>

            {/* Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
              <div className="bg-gradient-to-br from-surface to-surface-hover border border-border rounded-xl p-5 hover:border-primary/30 transition-all duration-300 group">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-primary-bg rounded-xl group-hover:scale-110 transition-transform duration-300">
                    <Workflow size={22} className="text-primary" />
                  </div>
                  <div>
                    <div className="text-3xl font-bold text-text-primary font-heading">{workflows.length}</div>
                    <div className="text-xs text-text-muted mt-0.5">Total Workflows</div>
                  </div>
                </div>
              </div>
              <div className="bg-gradient-to-br from-surface to-surface-hover border border-border rounded-xl p-5 hover:border-success/30 transition-all duration-300 group">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-success-bg rounded-xl group-hover:scale-110 transition-transform duration-300">
                    <Zap size={22} className="text-success" />
                  </div>
                  <div>
                    <div className="text-3xl font-bold text-text-primary font-heading">{activeWorkflows}</div>
                    <div className="text-xs text-text-muted mt-0.5">Active</div>
                  </div>
                </div>
              </div>
              <div className="bg-gradient-to-br from-surface to-surface-hover border border-border rounded-xl p-5 hover:border-accent/30 transition-all duration-300 group">
                <div className="flex items-center gap-4">
                  <div className="p-3 bg-accent-bg rounded-xl group-hover:scale-110 transition-transform duration-300">
                    <Clock size={22} className="text-accent" />
                  </div>
                  <div>
                    <div className="text-3xl font-bold text-text-primary font-heading">
                      {recentExecutions.length}
                    </div>
                    <div className="text-xs text-text-muted mt-0.5">Total Runs</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex gap-3">
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary-hover text-white font-medium rounded-xl transition-all duration-200 shadow-lg shadow-primary/20 hover:shadow-primary/30"
              >
                <Plus size={18} />
                New Workflow
              </button>
            </div>
          </div>
        </div>

        {/* Workflows Section */}
        <div className="px-6 py-6">
          <div className="max-w-5xl mx-auto">
            {error && (
              <div className="p-3 mb-6 bg-error-bg border border-error rounded-lg text-error-text text-sm">
                {error}
              </div>
            )}

            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-20 gap-4">
                <div className="w-10 h-10 border-3 border-border border-t-primary rounded-full animate-spin" />
                <p className="text-text-muted">Loading workflows...</p>
              </div>
            ) : workflows.length === 0 ? (
              /* Empty State */
              <div className="flex flex-col items-center justify-center py-16 gap-4 text-center animate-fade-in">
                <div className="w-16 h-16 bg-primary-bg rounded-2xl flex items-center justify-center mb-2">
                  <Workflow size={32} className="text-primary" />
                </div>
                <h3 className="text-xl font-semibold text-text-primary">No workflows yet</h3>
                <p className="text-text-muted max-w-md">
                  Create your first workflow to automate tasks. Click the button below to get started.
                </p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary-hover text-white font-medium rounded-lg transition-colors mt-2"
                >
                  <Plus size={18} />
                  Create Your First Workflow
                </button>
                <div className="mt-4 p-4 bg-surface border border-border rounded-xl text-sm text-text-muted max-w-sm animate-fade-in">
                  <p className="font-medium text-text-secondary mb-2">How it works:</p>
                  <ol className="space-y-1 text-left list-decimal list-inside text-text-muted">
                    <li>Create a workflow</li>
                    <li>Add nodes from the palette</li>
                    <li>Connect nodes by dragging</li>
                    <li>Configure each node</li>
                    <li>Run your workflow</li>
                  </ol>
                </div>
              </div>
            ) : (
              <>
                {/* Search + Sort Bar */}
                <div className="flex items-center gap-3 mb-4">
                  <div className="relative flex-1 max-w-sm">
                    <Search
                      size={16}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none"
                    />
                    <input
                      type="text"
                      placeholder="Search workflows..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-10 pr-3 py-2.5 bg-surface border border-border-hover rounded-xl text-sm text-text-primary placeholder:text-text-muted focus:border-primary focus:ring-2 focus:ring-primary-bg outline-none transition-all"
                    />
                  </div>

                  <div className="flex items-center gap-1 bg-surface border border-border rounded-xl p-0.5">
                    {([
                      { key: 'updated_at', label: 'Recent' },
                      { key: 'name', label: 'Name' },
                      { key: 'created_at', label: 'Created' },
                    ] as const).map((opt) => (
                      <button
                        key={opt.key}
                        onClick={() => {
                          if (sortKey === opt.key) {
                            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                          } else {
                            setSortKey(opt.key);
                            setSortOrder('desc');
                          }
                        }}
                        className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                          sortKey === opt.key
                            ? 'bg-primary text-white'
                            : 'text-text-muted hover:text-text-primary hover:bg-surface-hover'
                        }`}
                      >
                        {opt.label}
                        {sortKey === opt.key && (
                          <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>

                {/* No search results */}
                {filteredWorkflows.length === 0 && searchQuery && (
                  <div className="flex flex-col items-center py-12 gap-3 text-center">
                    <Search size={28} className="text-text-muted" />
                    <p className="text-text-muted">No workflows match "{searchQuery}"</p>
                  </div>
                )}

                {/* Workflow Grid */}
                {filteredWorkflows.length > 0 && (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {displayWorkflows.map((workflow) => (
                        <div
                          key={workflow.id}
                          onClick={() => navigate(`/workflow/${workflow.id}`)}
                          className="group bg-surface border border-border rounded-xl p-5 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5 cursor-pointer transition-all duration-300 relative overflow-hidden"
                        >
                          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                          <div className="relative">
                            <div className="flex items-start justify-between mb-3">
                              <h3 className="font-semibold text-text-primary group-hover:text-primary transition-colors truncate text-base">
                                {workflow.name}
                              </h3>
                              <span
                                className={`shrink-0 ml-2 px-2.5 py-0.5 text-xs font-medium rounded-full ${
                                  workflow.is_active
                                    ? 'bg-success-bg text-success-text'
                                    : 'bg-surface-hover text-text-muted'
                                }`}
                              >
                                {workflow.is_active ? 'Active' : 'Draft'}
                              </span>
                            </div>
                            {workflow.description && (
                              <p className="text-sm text-text-secondary mb-4 line-clamp-2 leading-relaxed">
                                {workflow.description}
                              </p>
                            )}
                            <div className="flex items-center justify-between pt-2 border-t border-border/50">
                              <span className="text-xs text-text-muted">
                                v{workflow.version} ·{' '}
                                {formatDate(workflow.updated_at)}
                              </span>
                              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    navigate(`/workflow/${workflow.id}`);
                                  }}
                                  className="p-1.5 text-text-muted hover:text-text-primary hover:bg-surface-hover rounded-lg transition-colors"
                                  title="Edit"
                                >
                                  <Settings size={14} />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setDeleteTarget(workflow);
                                  }}
                                  className="p-1.5 text-text-muted hover:text-error hover:bg-error-bg rounded-lg transition-colors"
                                  title="Delete"
                                >
                                  <Trash2 size={14} />
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* View All / Show Less */}
                    {filteredWorkflows.length > 6 && (
                      <div className="flex justify-center mt-6">
                        <button
                          onClick={() => setShowAll(!showAll)}
                          className="inline-flex items-center gap-2 px-4 py-2 text-sm text-text-secondary hover:text-text-primary hover:bg-surface-hover rounded-lg transition-colors"
                        >
                          {showAll ? (
                            <>Show Less</>
                          ) : (
                            <>
                              View All {filteredWorkflows.length} Workflows
                              <ArrowRight size={16} />
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </>
                )}
              </>
            )}
          </div>
        </div>
      </main>

      {/* Create Workflow Modal */}
      <Modal open={showCreateModal} onClose={closeCreateModal} title="Create New Workflow">
        <form onSubmit={createWorkflow} className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="name" className="block text-sm font-medium text-text-secondary">
              Name
            </label>
            <input
              id="name"
              type="text"
              value={newWorkflowName}
              onChange={(e) => setNewWorkflowName(e.target.value)}
              placeholder="My Workflow"
              required
              autoFocus
              className="w-full px-3 py-2 bg-bg border border-border rounded-xl text-text-primary focus:border-primary focus:ring-2 focus:ring-primary-bg outline-none transition-all"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="desc" className="block text-sm font-medium text-text-secondary">
              Description (optional)
            </label>
            <input
              id="desc"
              type="text"
              value={newWorkflowDesc}
              onChange={(e) => setNewWorkflowDesc(e.target.value)}
              placeholder="What does this workflow do?"
              className="w-full px-3 py-2 bg-bg border border-border rounded-xl text-text-primary focus:border-primary focus:ring-2 focus:ring-primary-bg outline-none transition-all"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={closeCreateModal}
              className="px-4 py-2 text-sm font-medium text-text-secondary hover:bg-surface-hover rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm font-medium bg-primary hover:bg-primary-hover text-white rounded-xl transition-colors"
            >
              Create
            </button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirm Dialog */}
      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
        title="Delete Workflow"
        message={`Delete "${deleteTarget?.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        loading={deleting}
      />
    </div>
  );
}
