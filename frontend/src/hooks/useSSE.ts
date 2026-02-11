import { useEffect, useRef, useState } from "react";

type SSEStatus = "connecting" | "connected" | "disconnected";

interface SSEEvent {
  type: string;
  data: unknown;
  timestamp: number;
}

export function useSSE(url: string, enabled = true) {
  const [status, setStatus] = useState<SSEStatus>("disconnected");
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
  const retryRef = useRef(0);
  const maxRetries = 5;
  const baseDelay = 1000;

  useEffect(() => {
    if (!enabled) {
      setStatus("disconnected");
      return;
    }

    let es: EventSource | null = null;
    let timeoutId: ReturnType<typeof setTimeout>;

    function connect() {
      setStatus("connecting");
      es = new EventSource(url);

      es.onopen = () => {
        setStatus("connected");
        retryRef.current = 0;
      };

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as unknown;
          setLastEvent({ type: event.type, data, timestamp: Date.now() });
        } catch {
          setLastEvent({ type: event.type, data: event.data, timestamp: Date.now() });
        }
      };

      es.onerror = () => {
        es?.close();
        setStatus("disconnected");
        if (retryRef.current < maxRetries) {
          const delay = baseDelay * Math.pow(2, retryRef.current);
          retryRef.current += 1;
          timeoutId = setTimeout(connect, delay);
        }
      };
    }

    connect();

    return () => {
      es?.close();
      clearTimeout(timeoutId);
    };
  }, [url, enabled]);

  return { status, lastEvent };
}
