import { useState, useCallback } from 'react';
import { Check, AlertCircle, Braces } from 'lucide-react';
import { useCredentialPicker } from '../hooks/useCredentialPicker';
import type { Credential } from '../hooks/useCredentialPicker';
import { CredentialPicker } from './CredentialPicker';

interface BodyEditorProps {
  value: any;
  onChange: (body: any) => void;
  credentials?: Credential[];
}

export function BodyEditor({ value, onChange, credentials = [] }: BodyEditorProps) {
  const [jsonError, setJsonError] = useState<string | null>(null);
  const { openPicker, togglePicker, insertCredential, registerRef } = useCredentialPicker();

  const getStringValue = useCallback(() => {
    if (typeof value === 'string') return value;
    if (value === null || value === undefined) return '';
    return JSON.stringify(value, null, 2);
  }, [value]);

  const handleChange = (text: string) => {
    if (!text.trim()) {
      setJsonError(null);
      onChange(null);
      return;
    }
    try {
      const parsed = JSON.parse(text);
      setJsonError(null);
      onChange(parsed);
    } catch (e: any) {
      setJsonError(e.message);
      // Still pass the raw string for editing
      onChange(text);
    }
  };

  const formatJson = () => {
    const str = getStringValue();
    if (!str) return;
    try {
      const parsed = JSON.parse(str);
      const formatted = JSON.stringify(parsed, null, 2);
      onChange(formatted);
      setJsonError(null);
    } catch {
      // Can't format invalid JSON
    }
  };

  return (
    <div className="space-y-1">
      <div className="relative">
        <textarea
          value={getStringValue()}
          onChange={(e) => handleChange(e.target.value)}
          ref={(el) => registerRef('body', el)}
          rows={6}
          placeholder='{ "key": "value" }'
          spellCheck={false}
          className="w-full px-3 py-2 bg-bg border border-border rounded-lg text-text-primary font-mono text-xs focus:border-primary focus:ring-2 focus:ring-primary-bg outline-none transition-all resize-y pr-24"
        />
        {/* Toolbar */}
        <div className="absolute top-1 right-1 flex items-center gap-1">
          <button
            type="button"
            onClick={formatJson}
            className="p-1.5 text-text-muted hover:text-text-primary hover:bg-surface-hover rounded transition-colors"
            title="Format JSON"
          >
            <Braces size={14} />
          </button>
          <CredentialPicker
            credentials={credentials}
            isOpen={openPicker === 'body'}
            onToggle={() => togglePicker('body')}
            onSelect={(credId) => {
              const currentVal = getStringValue();
              insertCredential('body', credId, currentVal, handleChange);
            }}
          />
        </div>
      </div>
      {/* Validation indicator */}
      <div className="flex items-center gap-1.5 px-1">
        {jsonError ? (
          <>
            <AlertCircle size={12} className="text-error shrink-0" />
            <span className="text-xs text-error truncate">{jsonError}</span>
          </>
        ) : getStringValue().trim() ? (
          <>
            <Check size={12} className="text-success shrink-0" />
            <span className="text-xs text-success">Valid JSON</span>
          </>
        ) : null}
      </div>
    </div>
  );
}
