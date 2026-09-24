import { useEffect, useState } from 'react';
import api from '../lib/api';
import {
  Play,
  Globe,
  Shuffle,
  GitBranch,
  Clock,
  Send,
  GripVertical,
} from 'lucide-react';

export interface NodeDef {
  node_type: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  input_schema: {
    properties: Record<string, {
      type: string;
      description?: string;
      default?: any;
      enum?: string[];
    }>;
    required?: string[];
  };
}

const ICON_MAP: Record<string, React.ReactNode> = {
  Play: <Play size={16} />,
  Globe: <Globe size={16} />,
  Shuffle: <Shuffle size={16} />,
  GitBranch: <GitBranch size={16} />,
  Clock: <Clock size={16} />,
  Send: <Send size={16} />,
};

export function NodePalette({ className = 'w-64', isMobile = false, onNodeClick }: { className?: string; isMobile?: boolean; onNodeClick?: (nodeType: string, label: string) => void }) {
  const [nodeDefs, setNodeDefs] = useState<NodeDef[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/nodes/')
      .then((res) => setNodeDefs(res.data))
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load nodes'))
      .finally(() => setIsLoading(false));
  }, []);

  const onDragStart = (e: React.DragEvent, node: NodeDef) => {
    e.dataTransfer.setData('application/reactflow-type', node.node_type);
    e.dataTransfer.setData('application/reactflow-label', node.name);
    e.dataTransfer.setData('application/reactflow-schema', JSON.stringify(node.input_schema));
    e.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className={`${className || 'w-64'} bg-surface border-r border-border flex flex-col h-full`}>
      <h3 className="px-4 py-3 font-semibold text-text-primary font-heading border-b border-border">
        Nodes
      </h3>
      <div className="flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-text-muted p-2">
            <div className="w-4 h-4 border-2 border-border border-t-primary rounded-full animate-spin" />
            Loading...
          </div>
        ) : error ? (
          <div className="text-sm text-error-text p-2">{error}</div>
        ) : (
              nodeDefs.map((node) => (
                <div
                  key={node.node_type}
                  className="flex items-center gap-3 p-2 rounded-lg cursor-grab hover:bg-surface-hover transition-colors"
                  draggable={!isMobile}
                  onDragStart={(e) => onDragStart(e, node)}
                  onClick={() => { if (isMobile) onNodeClick?.(node.node_type, node.name); }}
                >
                  <div className="text-text-muted">
                    {ICON_MAP[node.icon] || <GripVertical size={16} />}
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-text-primary">{node.name}</span>
                    <span className="text-xs text-text-muted">{node.category}</span>
                  </div>
                </div>
              ))
        )}
      </div>
      <div className="px-4 py-3 border-t border-border">
        <p className="text-xs text-text-muted">
          Tip: Drag nodes to the canvas to build your workflow. Connect them by dragging from one handle to another.
        </p>
      </div>
    </div>
  );
}
