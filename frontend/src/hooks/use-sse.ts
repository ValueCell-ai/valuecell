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
  /** Current error, if any */
  error: Error | null;
  /** Connect to the SSE endpoint */
  connect: (body?: BodyInit) => Promise<void>;
  /** Close the SSE connection */
  close: () => void;
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
  const [state, setState] = useState<SSEReadyState>(SSEReadyState.CLOSED);
  const handlersRef = useRef<SSEEventHandlers<T>>(handlers || {});
  const bodyRef = useRef<BodyInit | undefined>(body);

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
        setState(SSEReadyState.OPEN);
        handlersRef.current.onOpen?.();
      },
      onError: (err) => {
        setError(err);
        setState(SSEReadyState.CLOSED);
        handlersRef.current.onError?.(err);
      },
      onClose: () => {
        setState(SSEReadyState.CLOSED);
        handlersRef.current.onClose?.();
      },
    }),
    [],
  );

  // Create client instance (caller is responsible for options stability)
  const client = useMemo(
    () => new SSEClient<T>(options, internalHandlers),
    [options, internalHandlers],
  );

  // Cleanup on unmount or client change
  useEffect(() => {
    return () => {
      client.destroy();
    };
  }, [client]);

  // Auto-connect if enabled
  useEffect(() => {
    if (autoConnect) {
      setState(SSEReadyState.CONNECTING);
      void client.connect(bodyRef.current);
    }
  }, [autoConnect, client]);

  const connect = useCallback(
    async (connectBody?: BodyInit) => {
      setError(null);
      try {
        setState(SSEReadyState.CONNECTING);
        await client.connect(connectBody ?? bodyRef.current);
      } catch (err) {
        setError(err as Error);
        setState(SSEReadyState.CLOSED);
        throw err;
      }
    },
    [client],
  );

  const close = useCallback(() => {
    client.close();
    setState(SSEReadyState.CLOSED);
  }, [client]);

  return {
    state,
    error,
    connect,
    close,
    client,
  };
}

export default useSSE;
