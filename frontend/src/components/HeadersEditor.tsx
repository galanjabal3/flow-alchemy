import { Plus, X } from 'lucide-react';
import { useCredentialPicker } from '../hooks/useCredentialPicker';
import type { Credential } from '../hooks/useCredentialPicker';
import { CredentialPicker } from './CredentialPicker';

interface HeadersEditorProps {
  value: Record<string, string>;
  onChange: (headers: Record<string, string>) => void;
  credentials?: Credential[];
}

const DEFAULT_HEADERS = [
  { key: 'Content-Type', value: 'application/json', label: 'Content-Type' },
  { key: 'Authorization', value: 'Bearer ', label: 'Authorization' },
  { key: 'Accept', value: 'application/json', label: 'Accept' },
  { key: 'X-API-Key', value: '', label: 'X-API-Key' },
];

export function HeadersEditor({ value = {}, onChange, credentials = [] }: HeadersEditorProps) {
  const { openPicker, togglePicker, insertCredential, registerRef } = useCredentialPicker();

  const entries = Object.entries(value);
  const hasHeaders = entries.length > 0;

  const addHeader = (key: string, val: string) => {
    if (key && !value[key]) {
      onChange({ ...value, [key]: val });
    }
  };

  const updateKey = (oldKey: string, newKey: string) => {
    if (oldKey === newKey) return;
    const newHeaders: Record<string, string> = {};
    for (const [k, v] of Object.entries(value)) {
      if (k === oldKey) {
        newHeaders[newKey] = v;
      } else {
        newHeaders[k] = v;
      }
    }
    onChange(newHeaders);
  };

  const updateValue = (key: string, val: string) => {
    onChange({ ...value, [key]: val });
  };

  const removeHeader = (key: string) => {
    const newHeaders = { ...value };
    delete newHeaders[key];
    onChange(newHeaders);
  };

  return (
    <div className="space-y-2">
      {/* Header rows */}
      {hasHeaders ? (
        <div className="space-y-1">
          {/* Column headers */}
          <div className="grid grid-cols-[1fr_1fr_60px] gap-2 px-1 text-xs font-medium text-text-muted uppercase">
            <span>Key</span>
            <span>Value</span>
            <span></span>
          </div>
          {entries.map(([key, val]) => (
            <div key={key} className="group grid grid-cols-[1fr_1fr_60px] gap-2 items-center">
              <input
                type="text"
                value={key}
                onChange={(e) => updateKey(key, e.target.value)}
                className="px-2.5 py-1.5 bg-bg border border-border rounded-lg text-sm text-text-primary font-mono focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all"
                placeholder="Header name"
              />
              <div className="relative flex items-center gap-1">
                <input
                  type="text"
                  value={val}
                  onChange={(e) => updateValue(key, e.target.value)}
                  ref={(el) => registerRef(key, el)}
                  className="flex-1 px-2.5 py-1.5 bg-bg border border-border rounded-lg text-sm text-text-primary font-mono focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all pr-8"
                  placeholder="Value"
                />
                <CredentialPicker
                  credentials={credentials}
                  isOpen={openPicker === key}
                  onToggle={() => togglePicker(key)}
                  onSelect={(credId) => insertCredential(key, credId, val, (newVal) => updateValue(key, newVal))}
                />
              </div>
              <button
                type="button"
                onClick={() => removeHeader(key)}
                className="p-1.5 text-text-muted hover:text-error hover:bg-error-bg rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                title="Remove header"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-xs text-text-muted py-2">No headers configured</div>
      )}

      {/* Quick-add buttons */}
      <div className="flex flex-wrap gap-1.5">
        <button
          type="button"
          onClick={() => {
            const newKey = `Header-${entries.length + 1}`;
            addHeader(newKey, '');
          }}
          className="inline-flex items-center gap-1 px-2 py-1 text-xs text-primary bg-primary-bg hover:bg-primary/20 rounded-md transition-colors"
        >
          <Plus size={10} />
          Custom
        </button>
        {DEFAULT_HEADERS.filter((h) => !value[h.key]).map((h) => (
          <button
            key={h.key}
            type="button"
            onClick={() => addHeader(h.key, h.value)}
            className="inline-flex items-center gap-1 px-2 py-1 text-xs text-text-secondary bg-surface-hover hover:bg-surface-active rounded-md transition-colors"
          >
            <Plus size={10} />
            {h.label}
          </button>
        ))}
      </div>
    </div>
  );
}
