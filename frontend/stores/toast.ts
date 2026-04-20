import { create } from "zustand";
import type { ToastVariant } from "@/hooks/use-toast";

export interface ToastItem {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
  duration: number;
}

interface ToastState {
  toasts: ToastItem[];
  addToast: (opts: Omit<ToastItem, "id">) => string;
  removeToast: (id: string) => void;
}

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  addToast: (opts) => {
    const id = crypto.randomUUID();
    const item: ToastItem = { ...opts, id, duration: opts.duration ?? 4000 };
    set((s) => ({ toasts: [...s.toasts, item] }));
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
    }, item.duration);
    return id;
  },
  removeToast: (id) => {
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
  },
}));
