import { Key } from 'lucide-react';
import type { Credential } from '../hooks/useCredentialPicker';

interface CredentialPickerProps {
  credentials: Credential[];
  isOpen: boolean;
  onToggle: () => void;
  onSelect: (credId: number) => void;
  className?: string;
}

export function CredentialPicker({
  credentials,
  isOpen,
  onToggle,
  onSelect,
  className = '',
}: CredentialPickerProps) {
  if (credentials.length === 0) return null;

  return (
    <div className={`relative ${className}`}>
      <button
        type="button"
        onClick={onToggle}
        className="p-1.5 text-accent hover:bg-accent-bg rounded transition-colors"
        title="Insert credential"
      >
        <Key size={14} />
      </button>
      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={onToggle} />
          <div className="absolute z-50 top-full right-0 mt-1 w-56 bg-surface border border-border rounded-lg shadow-lg animate-scale-in">
            <div className="p-1 max-h-40 overflow-y-auto">
              {credentials.map((cred) => (
                <button
                  key={cred.id}
                  type="button"
                  onClick={() => onSelect(cred.id)}
                  className="w-full text-left px-3 py-1.5 text-sm text-text-primary hover:bg-surface-hover rounded-md transition-colors flex items-center gap-2"
                >
                  <Key size={12} className="text-accent shrink-0" />
                  <span className="truncate">{cred.name}</span>
                  <span className="text-xs text-text-muted ml-auto shrink-0">{cred.credential_type}</span>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
