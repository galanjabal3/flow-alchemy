import { useState, useEffect } from 'react';
import { getSchedule, setSchedule as setScheduleApi, deleteSchedule } from '../lib/api';
import type { ScheduleResponse } from '../lib/api';
import { useToast } from '../contexts/ToastContext';
import { ConfirmDialog } from './ConfirmDialog';
import { Clock, Trash2, Loader2, AlertCircle, CheckCircle } from 'lucide-react';

interface SchedulerPanelProps {
  workflowId: number;
  isTabActive?: boolean;
}

// Basic cron regex: 5 or 6 fields (minute hour day month day-of-week [year])
const CRON_REGEX = /^\s*(\*|[\d,\-/]+)\s+(\*|[\d,\-/]+)\s+(\*|[\d,\-/]+)\s+(\*|[\d,\-/]+)\s+(\*|[\d,\-/]+)(\s+(\*|[\d,\-/]+))?\s*$/;

export function SchedulerPanel({ workflowId, isTabActive = true }: SchedulerPanelProps) {
  const { showToast } = useToast();
  const [schedule, setSchedule] = useState<ScheduleResponse | null>(null);
  const [cronInput, setCronInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');
  const [validationError, setValidationError] = useState('');
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);

  // Load existing schedule on mount (only when active tab)
  useEffect(() => {
    if (!isTabActive) return;
    let cancelled = false;
    const doLoad = async () => {
      setLoading(true);
      setError('');
      try {
        const res = await getSchedule(workflowId);
        if (!cancelled) {
          setSchedule(res.data);
          setCronInput(res.data.schedule);
        }
      } catch {
        if (!cancelled) {
          setSchedule(null);
          setCronInput('');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    doLoad();
    return () => { cancelled = true; };
  }, [workflowId, isTabActive]);

  const handleSave = async () => {
    setValidationError('');
    setError('');

    const trimmed = cronInput.trim();
    if (!trimmed) {
      setValidationError('Cron expression is required');
      return;
    }

    // Client-side validation: basic cron format check
    if (!CRON_REGEX.test(trimmed)) {
      setValidationError('Invalid cron format. Use: * * * * * or * * * * * *');
      showToast('error', 'Invalid cron expression');
      return;
    }

    // Minimum interval check: reject schedules that are too frequent (< 5 min)
    const parts = trimmed.split(/\s+/);
    const minuteField = parts[0];
    if (minuteField !== '*' && !isFrequencyValid(minuteField)) {
      setValidationError('Schedule interval must be at least 5 minutes');
      showToast('error', 'Schedule interval must be at least 5 minutes');
      return;
    }

    setSaving(true);
    try {
      const res = await setScheduleApi(workflowId, trimmed);
      setSchedule(res.data);
      showToast('success', 'Schedule saved!');
    } catch (err: any) {
      // Backend returns 400 with detail like "too frequent"
      const msg = err.response?.data?.detail || 'Failed to set schedule';
      setError(msg);
      showToast('error', msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteSchedule(workflowId);
      setSchedule(null);
      setCronInput('');
      setShowConfirmDelete(false);
      showToast('success', 'Schedule removed');
    } catch {
      showToast('error', 'Failed to remove schedule');
    } finally {
      setDeleting(false);
    }
  };

  const isActive = schedule?.is_active ?? false;

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-3 p-8 text-text-muted">
        <div className="w-6 h-6 border-2 border-border border-t-primary rounded-full animate-spin" />
        <span className="text-sm">Loading scheduler...</span>
      </div>
    );
  }

  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock size={16} className="text-primary" />
          <h3 className="font-semibold text-text-primary font-heading">Schedule (Cron)</h3>
        </div>
        {isActive && (
          <span className="flex items-center gap-1.5 text-xs text-success bg-success-bg px-2 py-0.5 rounded-full">
            <CheckCircle size={12} /> Active
          </span>
        )}
      </div>

      <div className="p-4 space-y-4">
        {/* Cron Input Form */}
        <div className="space-y-2">
          <label className="text-sm text-text-secondary">Cron Expression</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={cronInput}
              onChange={(e) => { setCronInput(e.target.value); setValidationError(''); setError(''); }}
              placeholder="*/5 * * * *"
              className="flex-1 px-3 py-2.5 bg-bg border border-border rounded-lg text-sm text-text-primary font-mono focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all placeholder:text-text-muted"
            />
            <button
              onClick={handleSave}
              disabled={saving || deleting}
              className="px-4 py-2.5 bg-primary hover:bg-primary-hover text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors shrink-0"
            >
              {saving ? <Loader2 size={14} className="animate-spin mx-auto" /> : 'Save'}
            </button>
          </div>
          {validationError && (
            <p className="text-xs text-error flex items-center gap-1 animate-fade-in">
              <AlertCircle size={12} /> {validationError}
            </p>
          )}
          <p className="text-xs text-text-muted">
            Format: <code className="font-mono">minute hour day month dow</code> (5 fields) or add year as 6th. Minimum 5-minute interval.
          </p>
        </div>

        {/* Backend error message */}
        {error && !validationError && (
          <div className="p-3 bg-error-bg border border-error/30 rounded-lg text-sm text-error animate-fade-in">
            {error}
          </div>
        )}

        {/* Active Schedule Info */}
        {schedule && (
          <div className="bg-bg border border-border rounded-lg p-3 space-y-2 animate-fade-in">
            <div className="flex items-center justify-between text-sm">
              <span className="text-text-muted">Current Schedule</span>
              <code className="font-mono text-text-primary bg-surface-active px-2 py-0.5 rounded">{schedule.schedule}</code>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-text-muted">Next Run</span>
              <span className="text-text-primary">
                {schedule.next_run_at ? formatDateTime(schedule.next_run_at) : '—'}
              </span>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!schedule && (
          <div className="p-4 text-center bg-bg border border-border rounded-lg animate-fade-in">
            <Clock size={28} className="mx-auto mb-2 text-text-muted opacity-50" />
            <p className="text-sm text-text-secondary font-medium">No schedule set</p>
            <p className="text-xs text-text-muted mt-1">Add a cron expression above to enable scheduled execution</p>
          </div>
        )}

        {/* Remove Button */}
        {schedule && (
          <button
            onClick={() => setShowConfirmDelete(true)}
            disabled={deleting}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm text-error hover:bg-error-bg rounded-lg transition-colors disabled:opacity-50"
          >
            <Trash2 size={14} />
            {deleting ? 'Removing...' : 'Remove Schedule'}
          </button>
        )}
      </div>

      <ConfirmDialog
        open={showConfirmDelete}
        onClose={() => setShowConfirmDelete(false)}
        onConfirm={handleDelete}
        title="Remove Schedule"
        message="Are you sure you want to remove this schedule? The workflow will stop running on its cron timer."
        confirmLabel="Remove"
        cancelLabel="Keep"
        variant="danger"
        loading={deleting}
      />
    </div>
  );
}

// Check if the minute field allows >= 5 minute intervals
function isFrequencyValid(minuteField: string): boolean {
  const stepMatch = minuteField.match(/^\*\/(\d+)$/);
  if (stepMatch) {
    return parseInt(stepMatch[1], 10) >= 5;
  }
  return true;
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const pad = (n: number) => n < 10 ? `0${n}` : `${n}`;
  return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
