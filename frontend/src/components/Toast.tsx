import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

export interface ToastItem {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}

interface ToastProps {
  toast: ToastItem;
  onDismiss: (id: string) => void;
}

const TOAST_STYLES = {
  success: {
    bg: 'bg-success-bg border-success/30',
    icon: <CheckCircle size={16} className="text-success shrink-0" />,
  },
  error: {
    bg: 'bg-error-bg border-error/30',
    icon: <XCircle size={16} className="text-error shrink-0" />,
  },
  warning: {
    bg: 'bg-warning-bg border-warning/30',
    icon: <AlertTriangle size={16} className="text-warning shrink-0" />,
  },
  info: {
    bg: 'bg-info-bg border-info/30',
    icon: <Info size={16} className="text-info shrink-0" />,
  },
};

function Toast({ toast, onDismiss }: ToastProps) {
  const [exiting, setExiting] = useState(false);
  const style = TOAST_STYLES[toast.type];
  const duration = toast.duration ?? 4000;

  useEffect(() => {
    const timer = setTimeout(() => {
      setExiting(true);
      setTimeout(() => onDismiss(toast.id), 300);
    }, duration);
    return () => clearTimeout(timer);
  }, [duration, toast.id, onDismiss]);

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 border rounded-xl shadow-lg min-w-[280px] max-w-sm ${style.bg} ${exiting ? 'animate-toast-out' : 'animate-toast-in'}`}
    >
      {style.icon}
      <span className="text-sm text-text-primary flex-1">{toast.message}</span>
      <button
        onClick={() => { setExiting(true); setTimeout(() => onDismiss(toast.id), 300); }}
        className="p-0.5 text-text-muted hover:text-text-primary transition-colors shrink-0"
      >
        <X size={14} />
      </button>
    </div>
  );
}

export { Toast };
