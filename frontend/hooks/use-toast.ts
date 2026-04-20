"use client";

import { useCallback } from "react";
import { useToastStore } from "@/stores/toast";

export type ToastVariant = "success" | "error" | "info";

export interface ToastOptions {
  title: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
}

export function useToast() {
  const addToast = useToastStore((s) => s.addToast);
  const removeToast = useToastStore((s) => s.removeToast);

  const toast = useCallback(
    (opts: ToastOptions) => {
      const id = addToast({
        title: opts.title,
        description: opts.description,
        variant: opts.variant ?? "info",
        duration: opts.duration ?? 4000,
      });
      return id;
    },
    [addToast],
  );

  const dismiss = useCallback(
    (id: string) => {
      removeToast(id);
    },
    [removeToast],
  );

  return { toast, dismiss };
}
