import type { WsEnvelope, WsUserMessage } from '@ai-avatar/shared';

export type WsClientListener = (message: WsEnvelope) => void;

export interface WsClientOptions {
  url: string;
  token?: string;
  autoReconnect?: boolean;
  reconnectDelay?: number;
  maxReconnectAttempts?: number;
}

export class WsClient {
  private ws: WebSocket | null = null;
  private options: Required<WsClientOptions>;
  private listeners: Set<WsClientListener> = new Set();
  private reconnectAttempts = 0;
  private reconnectTimeout: number | null = null;
  private manualClose = false;

  constructor(options: WsClientOptions) {
    this.options = {
      url: options.url,
      token: options.token || '',
      autoReconnect: options.autoReconnect ?? true,
      reconnectDelay: options.reconnectDelay ?? 1000,
      maxReconnectAttempts: options.maxReconnectAttempts ?? 5,
    };
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.manualClose = false;
    const url = this.options.token
      ? `${this.options.url}?token=${this.options.token}`
      : this.options.url;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      console.log('[WsClient] Connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WsEnvelope;
        this.listeners.forEach((listener) => listener(message));
      } catch (error) {
        console.error('[WsClient] Failed to parse message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('[WsClient] Error:', error);
    };

    this.ws.onclose = () => {
      console.log('[WsClient] Disconnected');
      this.ws = null;

      if (!this.manualClose && this.options.autoReconnect) {
        this.scheduleReconnect();
      }
    };
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      console.warn('[WsClient] Max reconnect attempts reached');
      this.listeners.forEach((listener) =>
        listener({
          type: 'error',
          message: 'Max reconnect attempts reached',
          code: 'MAX_RECONNECT',
        })
      );
      return;
    }

    const delay = this.options.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    this.reconnectAttempts++;

    console.log(`[WsClient] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    this.reconnectTimeout = window.setTimeout(() => {
      this.connect();
    }, delay);
  }

  send(message: WsUserMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('[WsClient] Cannot send message, not connected');
      throw new Error('WebSocket is not connected');
    }
  }

  addListener(listener: WsClientListener): void {
    this.listeners.add(listener);
  }

  removeListener(listener: WsClientListener): void {
    this.listeners.delete(listener);
  }

  close(): void {
    this.manualClose = true;
    if (this.reconnectTimeout !== null) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

