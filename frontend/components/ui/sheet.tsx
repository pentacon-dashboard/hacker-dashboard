"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface SheetProps {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  side?: "left" | "right";
}

export function Sheet({ open, onClose, children, side = "left" }: SheetProps) {
  // 열릴 때 body 스크롤 잠금
  React.useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  // ESC 키 닫기
  React.useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (open) document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true">
      {/* 오버레이 */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* 패널 */}
      <div
        className={cn(
          "absolute top-0 h-full w-64 bg-background shadow-xl",
          "animate-in duration-200",
          side === "left"
            ? "left-0 slide-in-from-left-4"
            : "right-0 slide-in-from-right-4",
        )}
      >
        {children}
      </div>
    </div>
  );
}
