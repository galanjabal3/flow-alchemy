import { useEffect, useRef, useCallback, type ReactNode } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  size?: 'sm' | 'md' | 'lg';
  showClose?: boolean;
}

const SIZE_MAP = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
};

export function Modal({ open, onClose, title, children, size = 'md', showClose = true }: ModalProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.stopPropagation();
      onClose();
    }
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    previousActiveElement.current = document.activeElement as HTMLElement;
    document.addEventListener('keydown', handleEscape, true);
    document.documentElement.style.overflow = 'hidden';
    // Focus the card after render
    requestAnimationFrame(() => cardRef.current?.focus());
    return () => {
      document.removeEventListener('keydown', handleEscape, true);
      document.documentElement.style.overflow = '';
      previousActiveElement.current?.focus();
    };
  }, [open, handleEscape]);

  // Focus trap
  useEffect(() => {
    if (!open) return;
    const card = cardRef.current;
    if (!card) return;

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      const focusable = card.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    card.addEventListener('keydown', handleTab);
    return () => card.removeEventListener('keydown', handleTab);
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 flex items-center justify-center z-50 p-4 animate-modal-backdrop"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/50" />
      <div
        ref={cardRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
        className={`relative w-full ${SIZE_MAP[size]} bg-surface border border-border rounded-xl shadow-xl p-6 outline-none animate-modal-card`}
      >
        {(title || showClose) && (
          <div className="flex items-center justify-between mb-4">
            {title && (
              <h2 className="text-lg font-bold text-text-primary font-heading">{title}</h2>
            )}
            {showClose && (
              <button
                onClick={onClose}
                className="p-1 text-text-muted hover:text-text-primary hover:bg-surface-hover rounded-lg transition-colors ml-auto"
                aria-label="Close"
              >
                <X size={18} />
              </button>
            )}
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
