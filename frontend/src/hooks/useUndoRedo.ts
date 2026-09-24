import { useState, useRef, useCallback, useMemo } from 'react';
import type { Node, Edge } from '@xyflow/react';

export interface EditorSnapshot {
    nodes: Node[];
    edges: Edge[];
}

const MAX_HISTORY = 50;

export function useUndoRedo() {
    const undoStackRef = useRef<EditorSnapshot[]>([]);
    const redoStackRef = useRef<EditorSnapshot[]>([]);
    const [, setTick] = useState(0);

    const pushSnapshot = useCallback((nodes: Node[], edges: Edge[]) => {
        undoStackRef.current.push({
            nodes: JSON.parse(JSON.stringify(nodes)),
            edges: JSON.parse(JSON.stringify(edges)),
        });
        if (undoStackRef.current.length > MAX_HISTORY) {
            undoStackRef.current.shift();
        }
        redoStackRef.current = [];
        setTick((t) => t + 1);
    }, []);

    const undo = useCallback(() => {
        if (undoStackRef.current.length === 0) return null;
        const current = undoStackRef.current.pop()!;
        redoStackRef.current.push({
            nodes: JSON.parse(JSON.stringify(current.nodes)),
            edges: JSON.parse(JSON.stringify(current.edges)),
        });
        setTick((t) => t + 1);
        const prev = undoStackRef.current[undoStackRef.current.length - 1];
        if (prev) {
            return { nodes: JSON.parse(JSON.stringify(prev.nodes)), edges: JSON.parse(JSON.stringify(prev.edges)) };
        }
        return null;
    }, []);

    const redo = useCallback(() => {
        if (redoStackRef.current.length === 0) return null;
        const snapshot = redoStackRef.current.pop()!;
        undoStackRef.current.push({
            nodes: JSON.parse(JSON.stringify(snapshot.nodes)),
            edges: JSON.parse(JSON.stringify(snapshot.edges)),
        });
        setTick((t) => t + 1);
        return { nodes: JSON.parse(JSON.stringify(snapshot.nodes)), edges: JSON.parse(JSON.stringify(snapshot.edges)) };
    }, []);

    const reset = useCallback(() => {
        undoStackRef.current = [];
        redoStackRef.current = [];
        setTick((t) => t + 1);
    }, []);

    return useMemo(() => ({
        pushSnapshot, undo, redo, reset,
        get canUndo() { return undoStackRef.current.length > 0; },
        get canRedo() { return redoStackRef.current.length > 0; },
    }), [pushSnapshot, undo, redo, reset]);
}
