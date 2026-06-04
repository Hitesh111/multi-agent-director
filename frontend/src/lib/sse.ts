export type SseEvent =
  | { type: "execution.started"; data: { execution_id: number; workflow_name: string } }
  | { type: "execution.completed"; data: { execution_id: number; output_data: unknown } }
  | { type: "execution.failed"; data: { execution_id: number; error: string } }
  | { type: "execution.approved"; data: { execution_id: number; approved: boolean; feedback: string } }
  | { type: "node.status"; data: { execution_id: number; node_id: string; status: string } }
  | { type: "message.created"; data: { execution_id: number; node_id: string; agent_name: string; role: string; content: string; token_count: number } };

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function connectExecutionSse(
  executionId: number,
  onEvent: (event: SseEvent) => void,
  onError?: (err: Event) => void,
): { close: () => void } {
  const es = new EventSource(`${API_BASE}/api/executions/${executionId}/stream/`);

  es.onmessage = (msg) => {
    try {
      const parsed = JSON.parse(msg.data) as SseEvent;
      onEvent(parsed);
    } catch {
      console.warn("Invalid SSE message", msg.data);
    }
  };

  es.onerror = (err) => {
    onError?.(err);
  };

  return {
    close: () => {
      es.close();
    },
  };
}
