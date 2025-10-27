/**
 * Fetch-based SSE client library
 * Implements SSE using fetch + ReadableStream with custom headers and type safety
 */

import { parse } from "best-effort-json-parser";
import type { SSEData } from "@/types/agent";

export interface SSEOptions {
  /** SSE endpoint URL */
  url: string;
  /** Custom request headers */
  headers?: Record<string, string>;
  /** Handshake timeout in milliseconds */
  timeout?: number;
  /** Additional fetch request options */
  fetchOptions?: Omit<RequestInit, "method" | "body" | "headers" | "signal">;
}

export interface SSEEventHandlers {
  /** Called when SSE data is received */
  onData?: (data: SSEData) => void;
  /** Called when connection is established */
  onOpen?: () => void;
  /** Called when an error occurs */
  onError?: (error: Error) => void;
  /** Called when connection is closed */
  onClose?: () => void;
  /** Called when connection state changes */
  onStateChange?: (state: SSEReadyState) => void;
}

export enum SSEReadyState {
  CONNECTING = 0,
  OPEN = 1,
  CLOSED = 2,
}

export class SSEClient {
  private options: Required<SSEOptions>;
  private currentBody?: BodyInit;
  private handlers: SSEEventHandlers = {};
  private readyState: SSEReadyState = SSEReadyState.CLOSED;
  private abortController: AbortController | null = null;

  /**
   * Update ready state and notify handlers
   */
  private setReadyState(newState: SSEReadyState): void {
    if (this.readyState !== newState) {
      this.readyState = newState;
      this.handlers.onStateChange?.(newState);
    }
  }

  constructor(options: SSEOptions, handlers?: SSEEventHandlers) {
    this.options = this.resolveOptions(options);
    this.handlers = handlers ?? {};
  }

  private resolveOptions(options: SSEOptions): Required<SSEOptions> {
    return {
      url: options.url,
      timeout: options.timeout ?? 30 * 1000,
      headers: { ...(options.headers ?? {}) },
      fetchOptions: { ...(options.fetchOptions ?? {}) },
    };
  }

  /**
   * Connect to the SSE endpoint
   */
  async connect(body?: BodyInit): Promise<void> {
    // Prevent duplicate connections
    if (
      this.readyState === SSEReadyState.CONNECTING ||
      this.readyState === SSEReadyState.OPEN
    )
      return;

    this.currentBody = body;
    this.setReadyState(SSEReadyState.CONNECTING);
    this.abortController = new AbortController();

    // Start connection in the background; errors are handled via event handlers
    void this.startConnection().catch(() => {});
    return;
  }

  /**
   * Start the connection using fetch + ReadableStream
   */
  private async startConnection(): Promise<void> {
    let didTimeout = false;
    const timeoutId = setTimeout(() => {
      didTimeout = true;
      this.abortController?.abort();
    }, this.options.timeout);

    try {
      const response = await fetch(this.options.url, {
        method: "POST",
        body: this.currentBody,
        signal: this.abortController?.signal,
        ...this.options.fetchOptions,
        headers: {
          Accept: "text/event-stream",
          "Cache-Control": "no-cache",
          "Content-Type": "application/json",
          ...this.options.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error("Response body is empty");
      }

      // Connection established
      this.setReadyState(SSEReadyState.OPEN);
      this.handlers.onOpen?.();

      // Start reading the stream
      await this.readStream(response.body);
    } catch (error) {
      clearTimeout(timeoutId);
      this.setReadyState(SSEReadyState.CLOSED);

      if (error instanceof Error && error.name === "AbortError") {
        // Handshake timeout: emit error
        if (didTimeout) {
          const timeoutError = new Error("Handshake timeout");
          this.handlers.onError?.(timeoutError);
          return;
        }

        // Other aborts (e.g., superseded by a new connect): treat as normal close
        this.handlers.onClose?.();
        return;
      }

      // Other network/HTTP errors
      this.handlers.onError?.(error as Error);
      return;
    }
  }

  /**
   * Read the response stream and process SSE events
   */
  private async readStream(body: ReadableStream<Uint8Array>): Promise<void> {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          this.setReadyState(SSEReadyState.CLOSED);
          this.handlers.onClose?.();
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Process complete event blocks
        let eventEnd: number = buffer.indexOf("\n\n");
        while (eventEnd !== -1) {
          const eventBlock = buffer.slice(0, eventEnd);
          buffer = buffer.slice(eventEnd + 2);

          if (eventBlock.trim()) {
            this.processEvent(eventBlock);
          }

          eventEnd = buffer.indexOf("\n\n");
        }
      }
    } catch (error) {
      this.setReadyState(SSEReadyState.CLOSED);
      this.handlers.onError?.(error as Error);
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Process a single SSE event block
   */
  private processEvent(eventBlock: string): void {
    const lines = eventBlock.split("\n");
    let data = "";

    for (const line of lines) {
      if (line.startsWith("data:")) {
        data += `${line.slice(5).trim()}\n`;
      }
      // Ignore event: and retry: fields for simplicity
    }

    if (!data) return;

    // Remove trailing newline
    data = data.slice(0, -1);

    try {
      const parsedData = parse(data);

      // Pass through parsed payload without interpreting event names
      if (this.handlers.onData) {
        this.handlers.onData(parsedData as SSEData);
      }
    } catch (error) {
      // Only log JSON parsing errors, don't trigger connection-level error handling
      console.warn("Failed to parse SSE message:", data, error);
    }
  }

  /**
   * Get current connection state
   */
  get state(): SSEReadyState {
    return this.readyState;
  }

  /**
   * Close the SSE connection
   */
  close(): void {
    this.setReadyState(SSEReadyState.CLOSED);

    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }

    this.handlers.onClose?.();
  }

  /**
   * Destroy the client instance and clean up all resources
   */
  destroy(): void {
    this.close();
    this.handlers = {};
  }
}

export default SSEClient;
