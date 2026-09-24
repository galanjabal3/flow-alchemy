import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import {
  Play,
  Globe,
  Shuffle,
  GitBranch,
  Clock,
  Send,
} from 'lucide-react';

const ICON_MAP: Record<string, React.ReactNode> = {
  trigger: <Play size={14} />,
  http_request: <Globe size={14} />,
  transform: <Shuffle size={14} />,
  condition: <GitBranch size={14} />,
  delay: <Clock size={14} />,
  output: <Send size={14} />,
};

const NODE_DESCRIPTIONS: Record<string, string> = {
  trigger: 'Workflow entry point - starts the execution',
  http_request: 'Make HTTP requests to external APIs',
  transform: 'Transform and manipulate data',
  condition: 'Branch based on conditions',
  delay: 'Add delays between nodes',
  output: 'Send results to external services',
};

const COLOR_MAP: Record<string, { border: string; bg: string; text: string }> = {
  trigger: { border: 'var(--color-success)', bg: 'var(--color-success)', text: '#fff' },
  http_request: { border: 'var(--color-info)', bg: 'var(--color-info)', text: '#fff' },
  transform: { border: 'var(--color-warning)', bg: 'var(--color-warning)', text: '#fff' },
  condition: { border: 'var(--color-accent)', bg: 'var(--color-accent)', text: '#fff' },
  delay: { border: 'var(--color-secondary)', bg: 'var(--color-secondary)', text: '#fff' },
  output: { border: 'var(--color-error)', bg: 'var(--color-error)', text: '#fff' },
};

const FALLBACK_COLOR = { border: 'var(--color-secondary)', bg: 'var(--color-secondary)', text: '#fff' };

export function CustomNode({ data, type }: NodeProps) {
  const label = (data.label as string) || 'Untitled';
  const nodeType = (data.nodeType as string) || type || 'trigger';
  const icon = ICON_MAP[nodeType] || <Play size={14} />;
  const color = COLOR_MAP[nodeType] || FALLBACK_COLOR;

  return (
    <div
      className="bg-surface border-2 rounded-lg shadow-md min-w-[140px]"
      style={{ borderColor: color.border }}
      title={NODE_DESCRIPTIONS[nodeType] || nodeType.replace('_', ' ')}
    >
      <Handle type="target" position={Position.Top} id="top" />
      <Handle type="target" position={Position.Left} id="left" />
      <div
        className="flex items-center justify-center w-full h-8 rounded-t-[6px]"
        style={{ backgroundColor: color.bg, color: color.text }}
      >
        {icon}
      </div>
      <div className="px-3 py-2">
        <div className="text-sm font-medium text-text-primary">{label}</div>
        <div className="text-xs text-text-muted capitalize">{nodeType.replace('_', ' ')}</div>
      </div>
      <Handle type="source" position={Position.Bottom} id="bottom" />
      <Handle type="source" position={Position.Right} id="right" />
    </div>
  );
}
