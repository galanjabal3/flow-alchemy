import { useEffect, useRef, useCallback, useState } from 'react';

interface ExecutionEvent {
  execution_id: string;
  event_type: string;
  node_id?: string;
  status?: string;
  data?: any;
  timestamp?: string;
}

interface UseExecutionWebSocketOptions {
  executionId: string | null;
  token: string;
  onEvent?: (event: ExecutionEvent) => void;
  onStatusChange?: (status: string) => void;
  onNodeUpdate?: (nodeId: string, status: string, data?: any) => void;
}

const MAX_RETRIES = 5;
const TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled']);

export function useExecutionWebSocket({
  executionId,
  token,
  onEvent,
  onStatusChange,
  onNodeUpdate,
}: UseExecutionWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<ExecutionEvent | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCountRef = useRef(0);
  const terminalStatusRef = useRef(false);

  const connect = useCallback(() => {
    if (!executionId || !token || terminalStatusRef.current) return;
    if (retryCountRef.current >= MAX_RETRIES) return;

    const wsUrl = `${import.meta.env.VITE_API_URL?.replace('http', 'ws') || 'ws://localhost:8000'}/api/workflows/ws/executions/${executionId}?token=${token}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        retryCountRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastEvent(data);

          onEvent?.(data);
          if (data.status) {
            onStatusChange?.(data.status);
            if (TERMINAL_STATUSES.has(data.status)) {
              terminalStatusRef.current = true;
              ws.close();
              return;
            }
          }
          if (data.node_id && data.status) {
            onNodeUpdate?.(data.node_id, data.status, data.data);
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        setIsConnected(false);

        if (!terminalStatusRef.current && retryCountRef.current < MAX_RETRIES) {
          const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 10000);
          retryCountRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // ignore connection errors
    }
  }, [executionId, token, onEvent, onStatusChange, onNodeUpdate]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      terminalStatusRef.current = true;
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const sendPing = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send('ping');
    }
  }, []);

  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return {
    isConnected,
    lastEvent,
    sendPing,
    disconnect,
  };
}
