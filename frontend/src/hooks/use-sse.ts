import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import SSEClient, {
  type SSEEventHandlers,
  type SSEOptions,
  SSEReadyState,
} from "@/lib/sse-client";
import type { AgentEventMap } from "@/types/agent";

export interface UseSSEOptions<T = AgentEventMap[keyof AgentEventMap]> {
  /** SSE connection options */
  options: SSEOptions;
  /** Event handlers */
  handlers?: SSEEventHandlers<T>;
  /** Whether to auto-connect on mount */
  autoConnect?: boolean;
  /** Request body for POST requests */
  body?: BodyInit;
}

export interface UseSSEReturn<T = AgentEventMap[keyof AgentEventMap]> {
  /** Current connection state */
  state: SSEReadyState;
  /** Whether the connection is open */
  isConnected: boolean;
  /** Whether the connection is connecting */
  isConnecting: boolean;
  /** Number of reconnection attempts */
  reconnectAttempts: number;
  /** Current error, if any */
  error: Error | null;
  /** Connect to the SSE endpoint */
  connect: (body?: BodyInit) => Promise<void>;
  /** Close the SSE connection */
  close: () => void;
  /** Update event handlers */
  setEventHandlers: (handlers: SSEEventHandlers<T>) => void;
  /** SSE client instance for advanced usage */
  client: SSEClient<T> | null;
}

/**
 * React hook for Server-Sent Events (SSE) using fetch-based SSEClient
 *
 * @example
 * ```tsx
 * import { useSSE } from '@/hooks/use-sse';
 * import type { AgentEventMap, SSEData } from '@/types/agent';
 *
 * function ChatComponent() {
 *   const { connect, close, isConnected, error } = useSSE<AgentEventMap[keyof AgentEventMap]>({
 *     options: {
 *       url: '/api/chat/stream',
 *       headers: { 'Authorization': 'Bearer token' }
 *     },
 *     handlers: {
 *       onData: (sseData: SSEData<AgentEventMap[keyof AgentEventMap]>) => {
 *         const { event, data } = sseData;
 *         if (event === 'message_chunk' || event === 'message') {
 *           console.log('New message chunk:', data.payload.content);
 *         } else if (event === 'tool_call_started') {
 *           console.log('Tool call started:', data.payload.tool_name);
 *         } else if (event === 'done') {
 *           console.log('Conversation completed:', data.conversation_id);
 *         }
 *       },
 *       onError: (error) => console.error('SSE Error:', error)
 *     },
 *     autoConnect: true,
 *     body: JSON.stringify({
 *       message: 'Hello',
 *       conversation_id: 'conv_123'
 *     })
 *   });
 *
 *   return (
 *     <div>
 *       <p>Status: {isConnected ? 'Connected' : 'Disconnected'}</p>
 *       {error && <p>Error: {error.message}</p>}
 *       <button onClick={() => connect()}>Connect</button>
 *       <button onClick={close}>Disconnect</button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useSSE<T = AgentEventMap[keyof AgentEventMap]>({
  options,
  handlers,
  autoConnect = false,
  body,
}: UseSSEOptions<T>): UseSSEReturn<T> {
  const [error, setError] = useState<Error | null>(null);

  const clientRef = useRef<SSEClient<T> | null>(null);
  const handlersRef = useRef<SSEEventHandlers<T>>(handlers || {});
  const bodyRef = useRef<BodyInit | undefined>(body);

  // Force re-render when client state changes
  const [, setForceUpdate] = useState({});
  const triggerUpdate = useCallback(() => setForceUpdate({}), []);

  // Update refs when props change
  useEffect(() => {
    handlersRef.current = handlers || {};
  }, [handlers]);

  useEffect(() => {
    bodyRef.current = body;
  }, [body]);

  // Internal handlers referencing handlersRef to avoid re-binding
  const internalHandlers: SSEEventHandlers<T> = useMemo(
    () => ({
      onData: (sseData) => {
        handlersRef.current.onData?.(sseData);
      },
      onOpen: () => {
        setError(null);
        triggerUpdate();
        handlersRef.current.onOpen?.();
      },
      onError: (err) => {
        setError(err);
        triggerUpdate();
        handlersRef.current.onError?.(err);
      },
      onClose: () => {
        triggerUpdate();
        handlersRef.current.onClose?.();
      },
      onReconnect: (attempt) => {
        triggerUpdate();
        handlersRef.current.onReconnect?.(attempt);
      },
    }),
    [triggerUpdate],
  );

  // Initialize client
  useEffect(() => {
    const client = new SSEClient<T>(options);
    clientRef.current = client;

    client.setEventHandlers(internalHandlers);

    // Auto-connect if enabled
    if (autoConnect) {
      client.connect(bodyRef.current).catch((err) => {
        console.error("Auto-connect failed:", err);
      });
    }

    return () => {
      client.destroy();
    };
  }, [options, autoConnect, internalHandlers]); // Caller is responsible for options stability

  const connect = useCallback(async (connectBody?: BodyInit) => {
    if (!clientRef.current) return;

    setError(null);
    try {
      await clientRef.current.connect(connectBody ?? bodyRef.current);
    } catch (err) {
      setError(err as Error);
      throw err;
    }
  }, []);

  const close = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.close();
    }
  }, []);

  const setEventHandlers = useCallback((newHandlers: SSEEventHandlers<T>) => {
    handlersRef.current = { ...handlersRef.current, ...newHandlers };
  }, []);

  // Get current state from client, not duplicate state
  const currentState = clientRef.current?.state ?? SSEReadyState.CLOSED;
  const currentReconnectAttempts = clientRef.current?.reconnectAttempts ?? 0;

  return {
    state: currentState,
    isConnected: currentState === SSEReadyState.OPEN,
    isConnecting: currentState === SSEReadyState.CONNECTING,
    reconnectAttempts: currentReconnectAttempts,
    error,
    connect,
    close,
    setEventHandlers,
    client: clientRef.current,
  };
}

export default useSSE;
