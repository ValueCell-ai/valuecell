import { useCallback, useRef, useState } from "react";
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
  isStreaming: boolean;
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
  body,
  ...sseOptions
}: UseSSEOptions): UseSSEReturn {
  const clientRef = useRef<SSEClient | null>(null);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);

  // Handle state changes from SSE client
  const handleStateChange = useCallback((state: SSEReadyState) => {
    console.log("🚀 ~ handleStateChange ~ state:", state);
    setIsStreaming(
      state === SSEReadyState.OPEN || state === SSEReadyState.CONNECTING,
    );
  }, []);

  // Initialize client once
  if (!clientRef.current) {
    clientRef.current = new SSEClient(sseOptions, {
      ...handlers,
      onError: (err: Error) => {
        handlers?.onError?.(err);
      },
      onOpen: () => {
        handlers?.onOpen?.();
      },
      onStateChange: handleStateChange,
    });
  }

  const connect = useCallback(
    async (connectBody?: BodyInit) => {
      const client = clientRef.current;
      if (!client) throw new Error("SSE client not initialized");

      await client.connect(connectBody || body);
    },
    [body],
  );

  const close = useCallback(() => {
    clientRef.current?.close();
  }, []);

  return {
    isStreaming,
    connect,
    close,
  };
}

export default useSSE;
