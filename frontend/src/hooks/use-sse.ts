import { useCallback, useEffect, useRef, useState } from "react";
import SSEClient, {
  type SSEEventHandlers,
  type SSEOptions,
  SSEReadyState,
} from "@/lib/sse-client";

export interface UseSSEOptions<TEventMap = Record<string, unknown>> {
  /** SSE connection options */
  options: SSEOptions;
  /** Event handlers */
  handlers?: SSEEventHandlers<TEventMap>;
  /** Whether to auto-connect on mount */
  autoConnect?: boolean;
  /** Request body for POST requests */
  body?: BodyInit;
}

export interface UseSSEReturn<TEventMap = Record<string, unknown>> {
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
  setEventHandlers: (handlers: SSEEventHandlers<TEventMap>) => void;
  /** SSE client instance for advanced usage */
  client: SSEClient<TEventMap> | null;
}

/**
 * React hook for Server-Sent Events (SSE) using fetch-based SSEClient
 *
 * @example
 * ```tsx
 * interface ChatEventMap {
 *   message_chunk: { content: string; messageId: number };
 *   done: { messageId: number };
 * }
 *
 * function ChatComponent() {
 *   const { connect, close, isConnected, error } = useSSE<ChatEventMap>({
 *     options: {
 *       url: '/api/chat/stream',
 *       headers: { 'Authorization': 'Bearer token' }
 *     },
 *     handlers: {
 *       onEvent: (eventType, data) => {
 *         if (eventType === 'message_chunk') {
 *           console.log('New chunk:', data.content);
 *         }
 *       },
 *       onError: (error) => console.error('SSE Error:', error)
 *     },
 *     autoConnect: true,
 *     body: JSON.stringify({ conversationId: 123 })
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
export function useSSE<TEventMap = Record<string, unknown>>({
  options,
  handlers,
  autoConnect = false,
  body,
}: UseSSEOptions<TEventMap>): UseSSEReturn<TEventMap> {
  const [error, setError] = useState<Error | null>(null);

  const clientRef = useRef<SSEClient<TEventMap> | null>(null);
  const handlersRef = useRef<SSEEventHandlers<TEventMap>>(handlers || {});
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

  // Create internal handlers that combine state updates with user handlers
  const createInternalHandlers = useCallback(
    (): SSEEventHandlers<TEventMap> => ({
      onEvent: (eventType, data) => {
        handlersRef.current.onEvent?.(eventType, data);
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
    const client = new SSEClient<TEventMap>(options);
    clientRef.current = client;

    client.setEventHandlers(createInternalHandlers());

    // Auto-connect if enabled
    if (autoConnect) {
      client.connect(bodyRef.current).catch((err) => {
        console.error("Auto-connect failed:", err);
      });
    }

    return () => {
      client.destroy();
    };
  }, [options, autoConnect, createInternalHandlers]); // options object dependency for proper recreation

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

  const setEventHandlers = useCallback(
    (newHandlers: SSEEventHandlers<TEventMap>) => {
      handlersRef.current = { ...handlersRef.current, ...newHandlers };

      if (clientRef.current) {
        clientRef.current.setEventHandlers(createInternalHandlers());
      }
    },
    [createInternalHandlers],
  );

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
