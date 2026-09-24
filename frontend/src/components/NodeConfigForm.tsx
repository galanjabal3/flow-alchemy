import { useCallback, useState, useRef, useEffect } from 'react';
import { Key, ChevronDown } from 'lucide-react';
import { HeadersEditor } from './HeadersEditor';
import { BodyEditor } from './BodyEditor';
import { DurationPicker } from './DurationPicker';
import { TransformParamsEditor } from './TransformParamsEditor';
import { useCredentialPicker } from '../hooks/useCredentialPicker';
import type { Credential } from '../hooks/useCredentialPicker';

interface InputSchema {
  properties?: Record<string, {
    type: string;
    description?: string;
    default?: any;
    enum?: string[];
  }>;
  required?: string[];
}

interface NodeConfigFormProps {
  nodeType: string;
  inputSchema?: InputSchema;
  config: Record<string, any>;
  onChange: (config: Record<string, any>) => void;
  credentials?: Credential[];
}

const CREDENTIAL_FIELDS = new Set(['url', 'authorization', 'token', 'api_key', 'webhook_url']);

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-success-bg text-success',
  POST: 'bg-info-bg text-info',
  PUT: 'bg-warning-bg text-warning',
  DELETE: 'bg-error-bg text-error',
  PATCH: 'bg-accent-bg text-accent',
};

function MethodSelect({ label, required, value, options, onChange, description }: {
  label: string;
  required: boolean;
  value: string;
  options: string[];
  onChange: (v: string) => void;
  description?: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div className="space-y-1" ref={ref}>
      <label className="block text-sm font-medium text-text-secondary">
        {label}
        {required && <span className="text-error ml-1">*</span>}
      </label>
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className={`w-full px-3 py-2 border border-border rounded-lg font-mono text-sm font-medium text-left flex items-center justify-between transition-all hover:border-border-hover focus:ring-2 focus:ring-primary-bg outline-none ${
            value ? METHOD_COLORS[value] || 'bg-bg text-text-primary' : 'bg-bg text-text-muted'
          }`}
        >
          <span>{value || 'Select...'}</span>
          <ChevronDown size={14} className={`shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
        {open && (
          <div className="absolute z-50 top-full left-0 mt-1 w-full bg-surface border border-border rounded-lg shadow-lg animate-scale-in overflow-hidden">
            {options.map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => { onChange(opt); setOpen(false); }}
                className={`w-full px-3 py-2 text-left text-sm font-mono font-medium flex items-center gap-2 transition-colors ${
                  value === opt ? 'bg-surface-hover' : 'hover:bg-surface-hover'
                } ${METHOD_COLORS[opt] || 'text-text-primary'}`}
              >
                {value === opt && <span className="text-primary">✓</span>}
                {opt}
              </button>
            ))}
          </div>
        )}
      </div>
      {description && (
        <span className="text-xs text-text-muted">{description}</span>
      )}
    </div>
  );
}

export function NodeConfigForm({ nodeType, inputSchema, config, onChange, credentials = [] }: NodeConfigFormProps) {
  const { properties = {}, required = [] } = inputSchema || {};
  const { openPicker, togglePicker, insertCredential, registerRef } = useCredentialPicker();

  const handleChange = useCallback((key: string, value: any) => {
    onChange({ ...config, [key]: value });
  }, [config, onChange]);

  const renderCredentialButton = (key: string) => {
    if (credentials.length === 0 || !CREDENTIAL_FIELDS.has(key.toLowerCase())) return null;

    return (
      <div className="relative mt-1">
        <button
          type="button"
          onClick={() => togglePicker(key)}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-accent bg-accent/10 hover:bg-accent/20 border border-accent/30 rounded-md transition-colors"
        >
          <Key size={12} />
          Insert Credential
          <ChevronDown size={10} className={`transition-transform ${openPicker === key ? 'rotate-180' : ''}`} />
        </button>

        {openPicker === key && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => togglePicker(key)} />
            <div className="absolute z-50 top-full left-0 mt-1 w-64 bg-surface border border-border rounded-lg shadow-lg animate-scale-in">
              <div className="p-1 max-h-48 overflow-y-auto">
                {credentials.map((cred) => (
                  <button
                    key={cred.id}
                    type="button"
                    onClick={() => {
                      const currentVal = config[key] || '';
                      insertCredential(key, cred.id, currentVal, (newVal) => handleChange(key, newVal));
                    }}
                    className="w-full text-left px-3 py-2 text-sm text-text-primary hover:bg-surface-hover rounded-md transition-colors flex items-center gap-2"
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
  };

  const renderField = (key: string, prop: { type: string; description?: string; default?: any; enum?: string[] }) => {
    const isRequired = required.includes(key);
    const value = config[key] ?? prop.default ?? '';

    // Special: HTTP method with colored badge
    if (key === 'method' && prop.enum) {
      return (
        <MethodSelect
          key={key}
          label={key}
          required={isRequired}
          value={value}
          options={prop.enum}
          onChange={(v) => handleChange(key, v)}
          description={prop.description}
        />
      );
    }

    // Special: duration fields (duration_ms, timeout)
    if ((key === 'duration_ms' || key === 'timeout') && (prop.type === 'integer' || prop.type === 'number')) {
      return (
        <div className="space-y-1" key={key}>
          <label className="block text-sm font-medium text-text-secondary">
            {key}
            {isRequired && <span className="text-error ml-1">*</span>}
          </label>
          <DurationPicker
            valueMs={value || (key === 'timeout' ? 30000 : 1000)}
            onChangeMs={(ms) => handleChange(key, ms)}
            max={300000}
          />
          {prop.description && (
            <span className="text-xs text-text-muted">{prop.description}</span>
          )}
        </div>
      );
    }

    // Special: headers object → HeadersEditor
    if (key === 'headers' && prop.type === 'object') {
      return (
        <div className="space-y-1" key={key}>
          <label className="block text-sm font-medium text-text-secondary">
            {key}
            {isRequired && <span className="text-error ml-1">*</span>}
          </label>
          <HeadersEditor
            value={typeof value === 'object' && value !== null ? value : {}}
            onChange={(headers) => handleChange(key, headers)}
            credentials={credentials}
          />
          {prop.description && (
            <span className="text-xs text-text-muted">{prop.description}</span>
          )}
        </div>
      );
    }

    // Special: body object → BodyEditor
    if (key === 'body' && prop.type === 'object') {
      return (
        <div className="space-y-1" key={key}>
          <label className="block text-sm font-medium text-text-secondary">
            {key}
            {isRequired && <span className="text-error ml-1">*</span>}
          </label>
          <BodyEditor
            value={value}
            onChange={(body) => handleChange(key, body)}
            credentials={credentials}
          />
          {prop.description && (
            <span className="text-xs text-text-muted">{prop.description}</span>
          )}
        </div>
      );
    }

    // Enum (non-method)
    if (prop.enum) {
      return (
        <div className="space-y-1" key={key}>
          <label className="block text-sm font-medium text-text-secondary">
            {key}
            {isRequired && <span className="text-error ml-1">*</span>}
          </label>
          <select
            value={value}
            onChange={(e) => handleChange(key, e.target.value)}
            className="w-full px-3 py-2 bg-bg border border-border rounded-lg text-text-primary focus:border-primary focus:ring-2 focus:ring-primary-bg outline-none transition-all"
          >
            <option value="">Select...</option>
            {prop.enum.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
          {prop.description && (
            <span className="text-xs text-text-muted">{prop.description}</span>
          )}
        </div>
      );
    }

    // Integer/Number (non-duration)
    if (prop.type === 'integer' || prop.type === 'number') {
      return (
        <div className="space-y-1" key={key}>
          <label className="block text-sm font-medium text-text-secondary">
            {key}
            {isRequired && <span className="text-error ml-1">*</span>}
          </label>
          <input
            type="number"
            value={value}
            onChange={(e) => handleChange(key, prop.type === 'integer' ? parseInt(e.target.value, 10) || 0 : parseFloat(e.target.value) || 0)}
            className="w-full px-3 py-2 bg-bg border border-border rounded-lg text-text-primary focus:border-primary focus:ring-2 focus:ring-primary-bg outline-none transition-all"
          />
          {prop.description && (
            <span className="text-xs text-text-muted">{prop.description}</span>
          )}
        </div>
      );
    }

    // Boolean
    if (prop.type === 'boolean') {
      return (
        <div className="flex items-center gap-2" key={key}>
          <input
            type="checkbox"
            checked={!!value}
            onChange={(e) => handleChange(key, e.target.checked)}
            className="w-4 h-4 rounded border-border bg-bg text-primary focus:ring-primary-bg"
          />
          <label className="text-sm font-medium text-text-secondary">
            {key}
            {isRequired && <span className="text-error ml-1">*</span>}
          </label>
          {prop.description && (
            <span className="text-xs text-text-muted">{prop.description}</span>
          )}
        </div>
      );
    }

    // Special: Transform params → TransformParamsEditor
    if (key === 'params' && nodeType === 'transform' && prop.type === 'object') {
      return (
        <div className="space-y-1" key={key}>
          <label className="block text-sm font-medium text-text-secondary">
            Parameters
            {isRequired && <span className="text-error ml-1">*</span>}
          </label>
          <TransformParamsEditor
            operation={config.operation || ''}
            params={typeof value === 'object' && value !== null ? value : {}}
            onChange={(params) => handleChange(key, params)}
          />
          {prop.description && (
            <span className="text-xs text-text-muted">{prop.description}</span>
          )}
        </div>
      );
    }

    // Object (generic fallback)
    if (prop.type === 'object') {
      return (
        <div className="space-y-1" key={key}>
          <label className="block text-sm font-medium text-text-secondary">
            {key}
            {isRequired && <span className="text-error ml-1">*</span>}
          </label>
          <BodyEditor
            value={value}
            onChange={(v) => handleChange(key, v)}
            credentials={credentials}
          />
          {prop.description && (
            <span className="text-xs text-text-muted">{prop.description}</span>
          )}
        </div>
      );
    }

    // Default: string input
    return (
      <div className="space-y-1" key={key}>
        <label className="block text-sm font-medium text-text-secondary">
          {key}
          {isRequired && <span className="text-error ml-1">*</span>}
        </label>
        <input
          type="text"
          value={value}
          placeholder={prop.description || ''}
          onChange={(e) => handleChange(key, e.target.value)}
          ref={(el) => registerRef(key, el)}
          className="w-full px-3 py-2 bg-bg border border-border rounded-lg text-text-primary focus:border-primary focus:ring-2 focus:ring-primary-bg outline-none transition-all"
        />
        {renderCredentialButton(key)}
        {prop.description && (
          <span className="text-xs text-text-muted">{prop.description}</span>
        )}
      </div>
    );
  };

  return (
    <div className="p-4 bg-surface border-t border-border">
      <div className="mb-3">
        <span className="px-2 py-1 text-xs font-medium bg-primary-bg text-primary rounded">{nodeType}</span>
      </div>
      {Object.entries(properties).length === 0 ? (
        <div className="text-sm text-text-muted">No configuration options</div>
      ) : (
        <div className="space-y-3">
          {Object.entries(properties).map(([key, prop]) => renderField(key, prop))}
        </div>
      )}
      {credentials.length > 0 && (
        <p className="mt-3 text-xs text-text-muted">
          Click <Key size={10} className="inline text-accent" /> button or type <code className="px-1 py-0.5 bg-bg rounded text-primary font-mono">{'{{cred:ID}}'}</code> to use credentials
        </p>
      )}
    </div>
  );
}
