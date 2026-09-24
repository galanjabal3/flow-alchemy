import { useEffect } from 'react';

interface TransformParamsEditorProps {
  operation: string;
  params: Record<string, any>;
  onChange: (params: Record<string, any>) => void;
}

const PARAMS_CONFIG: Record<string, Array<{ key: string; label: string; type: string; placeholder?: string; default?: any }>> = {
  filter: [
    { key: 'key', label: 'Field Key', type: 'text', placeholder: 'e.g. status' },
    { key: 'value', label: 'Match Value', type: 'text', placeholder: 'e.g. active' },
  ],
  map: [
    { key: 'field', label: 'Field to Extract', type: 'text', placeholder: 'e.g. name' },
  ],
  split: [
    { key: 'delimiter', label: 'Delimiter', type: 'text', placeholder: ', or | or space', default: ',' },
  ],
  merge: [
    { key: 'sources', label: 'Sources (JSON array)', type: 'textarea', placeholder: '[ {"key": "value"} ]' },
  ],
};

export function TransformParamsEditor({ operation, params, onChange }: TransformParamsEditorProps) {
  const fields = PARAMS_CONFIG[operation];

  // Reset params when operation changes
  useEffect(() => {
    if (!fields) {
      if (Object.keys(params).length > 0) {
        onChange({});
      }
      return;
    }
    // Initialize defaults for missing fields
    const updated = { ...params };
    let changed = false;
    for (const field of fields) {
      if (updated[field.key] === undefined && field.default !== undefined) {
        updated[field.key] = field.default;
        changed = true;
      }
    }
    if (changed) {
      onChange(updated);
    }
  }, [operation]);

  if (!fields) {
    return (
      <div className="text-xs text-text-muted py-2">
        No parameters needed for this operation
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {fields.map((field) => {
        const value = params[field.key] ?? field.default ?? '';

        if (field.type === 'textarea') {
          return (
            <div key={field.key} className="space-y-1">
              <label className="block text-xs font-medium text-text-secondary">{field.label}</label>
              <textarea
                value={typeof value === 'string' ? value : JSON.stringify(value, null, 2) || ''}
                placeholder={field.placeholder}
                onChange={(e) => {
                  try {
                    onChange({ ...params, [field.key]: JSON.parse(e.target.value) });
                  } catch {
                    onChange({ ...params, [field.key]: e.target.value });
                  }
                }}
                rows={3}
                className="w-full px-2.5 py-1.5 bg-bg border border-border rounded-lg text-sm text-text-primary font-mono text-xs focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all resize-y"
              />
            </div>
          );
        }

        return (
          <div key={field.key} className="space-y-1">
            <label className="block text-xs font-medium text-text-secondary">{field.label}</label>
            <input
              type="text"
              value={value}
              placeholder={field.placeholder}
              onChange={(e) => onChange({ ...params, [field.key]: e.target.value })}
              className="w-full px-2.5 py-1.5 bg-bg border border-border rounded-lg text-sm text-text-primary focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all"
            />
          </div>
        );
      })}
    </div>
  );
}
