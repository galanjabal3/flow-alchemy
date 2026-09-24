import { Modal } from './Modal';

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'info';
  loading?: boolean;
}

const VARIANT_STYLES = {
  danger: 'bg-error hover:bg-error/80 text-white',
  warning: 'bg-warning hover:bg-warning/80 text-white',
  info: 'bg-primary hover:bg-primary-hover text-white',
};

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'danger',
  loading = false,
}: ConfirmDialogProps) {
  return (
    <Modal open={open} onClose={onClose} title={title} size="sm" showClose={false}>
      <p className="text-sm text-text-secondary mb-6">{message}</p>
      <div className="flex justify-end gap-3">
        <button
          onClick={onClose}
          disabled={loading}
          className="px-4 py-2 text-sm font-medium text-text-secondary hover:bg-surface-hover rounded-lg transition-colors disabled:opacity-50"
        >
          {cancelLabel}
        </button>
        <button
          onClick={() => { onConfirm(); }}
          disabled={loading}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-50 ${VARIANT_STYLES[variant]}`}
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Processing...
            </span>
          ) : (
            confirmLabel
          )}
        </button>
      </div>
    </Modal>
  );
}
