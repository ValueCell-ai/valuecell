import { useCallback, useEffect, useRef, useState } from "react";
import SSEClient, {
  type SSEEventHandlers,
  type SSEOptions,
  SSEReadyState,
} from "@/lib/sse-client";

export interface UseSSEOptions extends SSEOptions {
  /** Event handlers */
  handlers?: SSEEventHandlers;
  /** Whether to auto-connect on mount */
  autoConnect?: boolean;
  /** Request body for POST requests */
  body?: BodyInit;
}

export interface UseSSEReturn {
  /** Current connection state */
  state: SSEReadyState;
  /** Whether the connection is open */
  isConnected: boolean;
  /** Current error, if any */
  error: Error | null;
  /** Connect to the SSE endpoint */
  connect: (body?: BodyInit) => Promise<void>;
  /** Close the SSE connection */
  close: () => void;
}

/**
 * React hook for Server-Sent Events (SSE) - simplified version
 */
export function useSSE({
  handlers,
  autoConnect = false,
  body,
  ...sseOptions
}: UseSSEOptions): UseSSEReturn {
  const [error, setError] = useState<Error | null>(null);
  const clientRef = useRef<SSEClient | null>(null);

  // Initialize client once
  if (!clientRef.current) {
    clientRef.current = new SSEClient(sseOptions, {
      ...handlers,
      onError: (err: Error) => {
        setError(err);
        handlers?.onError?.(err);
      },
      onOpen: () => {
        setError(null);
        handlers?.onOpen?.();
      },
    });
  }

  // Auto-connect and cleanup
  useEffect(() => {
    const client = clientRef.current!;

    if (autoConnect) {
      client.connect(body);
    }

    return () => {
      client.destroy();
      clientRef.current = null;
    };
  }, [autoConnect, body]);

  const connect = useCallback(
    async (connectBody?: BodyInit) => {
      const client = clientRef.current;
      if (!client) throw new Error("SSE client not initialized");

      setError(null);
      await client.connect(connectBody || body);
    },
    [body],
  );

  const close = useCallback(() => {
    clientRef.current?.close();
  }, []);

  const state = clientRef.current?.state ?? SSEReadyState.CLOSED;

  return {
    state,
    isConnected: state === SSEReadyState.OPEN,
    error,
    connect,
    close,
  };
}

export default useSSE;
