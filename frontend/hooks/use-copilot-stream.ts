"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface CopilotPlan {
  plan_id: string;
  session_id: string;
  steps: CopilotPlanStep[];
  created_at: string;
}

export interface CopilotPlanStep {
  step_id: string;
  agent: string;
  inputs: Record<string, unknown>;
  depends_on: string[];
  gate_policy: { schema: boolean; domain: boolean; critique: boolean };
}

export interface CopilotCard {
  type:
    | "text"
    | "chart"
    | "scorecard"
    | "citation"
    | "comparison_table"
    | "simulator_result"
    | "news_rag_list";
  degraded?: boolean;
  body?: string;
  content?: string;
  [key: string]: unknown;
}

export type CopilotEvent =
  | { type: "plan.ready"; plan: CopilotPlan }
  | { type: "step.start"; step_id: string }
  | { type: "step.token"; step_id: string; text: string }
  | {
      type: "step.gate";
      step_id: string;
      gate: "schema" | "domain" | "critique";
      status: "pass" | "fail" | "retry";
      reason?: string | null;
    }
  | { type: "step.result"; step_id: string; card: CopilotCard }
  | { type: "final.card"; card: CopilotCard }
  | { type: "error"; step_id?: string; code: string; message: string }
  | { type: "done"; session_id: string; turn_id: string };

export interface StepState {
  buffer: string;
  card: CopilotCard | null;
  degraded: boolean;
  gates: {
    schema?: "pass" | "fail" | "retry";
    domain?: "pass" | "fail" | "retry";
    critique?: "pass" | "fail" | "retry";
  };
}

export interface CopilotStreamState {
  status: "idle" | "streaming" | "completed" | "error";
  plan: CopilotPlan | null;
  steps: Record<string, StepState>;
  finalCard: CopilotCard | null;
  sessionId: string | null;
  turnId: string | null;
  degraded: { step_id: string; reason: string } | null;
  error: string | null;
}

export const initialCopilotState: CopilotStreamState = {
  status: "idle",
  plan: null,
  steps: {},
  finalCard: null,
  sessionId: null,
  turnId: null,
  degraded: null,
  error: null,
};

export function copilotStreamReducer(
  state: CopilotStreamState,
  event: CopilotEvent,
): CopilotStreamState {
  switch (event.type) {
    case "plan.ready":
      return {
        ...state,
        status: "streaming",
        plan: event.plan,
      };

    case "step.start": {
      const prev = state.steps[event.step_id] ?? {
        buffer: "",
        card: null,
        degraded: false,
        gates: {},
      };
      return {
        ...state,
        steps: {
          ...state.steps,
          [event.step_id]: { ...prev, buffer: "", card: null },
        },
      };
    }

    case "step.token": {
      const prev = state.steps[event.step_id] ?? {
        buffer: "",
        card: null,
        degraded: false,
        gates: {},
      };
      return {
        ...state,
        steps: {
          ...state.steps,
          [event.step_id]: { ...prev, buffer: prev.buffer + event.text },
        },
      };
    }

    case "step.gate": {
      const prev = state.steps[event.step_id] ?? {
        buffer: "",
        card: null,
        degraded: false,
        gates: {},
      };
      const newStepState: StepState = {
        ...prev,
        gates: { ...prev.gates, [event.gate]: event.status },
      };

      let newDegraded = state.degraded;
      if (event.status === "fail") {
        newStepState.degraded = true;
        newDegraded = {
          step_id: event.step_id,
          reason: event.reason ?? `${event.gate} gate failed`,
        };
      }

      return {
        ...state,
        steps: { ...state.steps, [event.step_id]: newStepState },
        degraded: newDegraded,
      };
    }

    case "step.result": {
      const prev = state.steps[event.step_id] ?? {
        buffer: "",
        card: null,
        degraded: false,
        gates: {},
      };
      const isCardDegraded = event.card.degraded === true;
      const newStepState: StepState = {
        ...prev,
        card: event.card,
        buffer: "",
        degraded: prev.degraded || isCardDegraded,
      };

      let newDegraded = state.degraded;
      if (isCardDegraded && !newDegraded) {
        newDegraded = {
          step_id: event.step_id,
          reason: "step result degraded",
        };
      }

      return {
        ...state,
        steps: { ...state.steps, [event.step_id]: newStepState },
        degraded: newDegraded,
      };
    }

    case "final.card":
      return {
        ...state,
        finalCard: event.card,
      };

    case "done":
      return {
        ...state,
        status: "completed",
        sessionId: event.session_id,
        turnId: event.turn_id,
      };

    case "error":
      return {
        ...state,
        error: event.message,
      };

    default:
      return state;
  }
}

export interface UseCopilotStreamOptions {
  onEvent?: (event: CopilotEvent) => void;
}

export function useCopilotStream(options?: UseCopilotStreamOptions) {
  const [state, setState] = useState<CopilotStreamState>(initialCopilotState);
  const eventSourceRef = useRef<EventSource | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  const query = useCallback(
    async (queryText: string, sessionId?: string) => {
      cleanup();
      setState(initialCopilotState);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await fetch("/api/copilot/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: queryText, session_id: sessionId }),
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          setState((s) => ({ ...s, status: "error", error: `HTTP ${res.status}` }));
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        setState((s) => ({ ...s, status: "streaming" }));

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const blocks = buffer.split("\n\n");
          buffer = blocks.pop() ?? "";

          for (const block of blocks) {
            if (!block.trim()) continue;
            for (const line of block.split("\n")) {
              if (!line.startsWith("data:")) continue;
              const payload = line.slice("data:".length).trim();
              if (!payload) continue;
              try {
                const event = JSON.parse(payload) as CopilotEvent;
                options?.onEvent?.(event);
                setState((s) => copilotStreamReducer(s, event));
              } catch {
                // Ignore malformed SSE frames and continue reading.
              }
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") return;
        setState((s) => ({
          ...s,
          status: "error",
          error: err instanceof Error ? err.message : "unknown error",
        }));
      }
    },
    [cleanup, options],
  );

  const reset = useCallback(() => {
    cleanup();
    setState(initialCopilotState);
  }, [cleanup]);

  return { state, query, reset, cleanup };
}
