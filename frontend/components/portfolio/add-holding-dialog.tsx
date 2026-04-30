"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { SymbolSearch } from "@/components/watchlist/symbol-search";
import { createHolding, type HoldingCreate } from "@/lib/api/portfolio";
import type { SymbolInfo } from "@/lib/api/symbols";

interface FormState {
  market: string;
  code: string;
  quantity: string;
  avgCost: string;
  currency: "KRW" | "USD" | "USDT";
}

const INITIAL_FORM: FormState = {
  market: "",
  code: "",
  quantity: "",
  avgCost: "",
  currency: "KRW",
};

interface FieldError {
  quantity?: string;
  avgCost?: string;
  symbol?: string;
}

function validate(form: FormState): FieldError {
  const errors: FieldError = {};
  if (!form.code) errors.symbol = "종목을 선택하세요.";
  const qty = Number(form.quantity);
  if (!form.quantity || isNaN(qty) || qty <= 0)
    errors.quantity = "수량은 0보다 커야 합니다.";
  const cost = Number(form.avgCost);
  if (!form.avgCost || isNaN(cost) || cost <= 0)
    errors.avgCost = "평단가는 0보다 커야 합니다.";
  return errors;
}

interface AddHoldingDialogProps {
  clientId?: string;
}

export function AddHoldingDialog({ clientId = "client-001" }: AddHoldingDialogProps) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [errors, setErrors] = useState<FieldError>({});
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (body: HoldingCreate) => createHolding(body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["portfolio", "summary"] });
      await queryClient.invalidateQueries({ queryKey: ["portfolio", "holdings"] });
      await queryClient.invalidateQueries({ queryKey: ["portfolio", "clients"] });
      setOpen(false);
      setForm(INITIAL_FORM);
      setErrors({});
    },
  });

  function handleSymbolSelect(symbol: SymbolInfo) {
    setForm((prev) => ({
      ...prev,
      market: symbol.market ?? "",
      code: symbol.symbol,
    }));
    setErrors((prev) => ({ ...prev, symbol: undefined }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const fieldErrors = validate(form);
    if (Object.keys(fieldErrors).length > 0) {
      setErrors(fieldErrors);
      return;
    }
    const body: HoldingCreate = {
      client_id: clientId,
      market: form.market,
      code: form.code,
      quantity: form.quantity,
      avg_cost: form.avgCost,
      currency: form.currency,
    };
    mutation.mutate(body);
  }

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (!next) {
      setForm(INITIAL_FORM);
      setErrors({});
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button data-testid="add-holding-button" size="sm">
          + 보유자산 추가
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>보유자산 추가</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 심볼 검색 */}
          <div className="space-y-1">
            <label className="text-sm font-medium">종목</label>
            <SymbolSearch onSelect={handleSymbolSelect} />
            {form.code && (
              <p className="text-xs text-muted-foreground">
                선택됨: {form.code} ({form.market})
              </p>
            )}
            {errors.symbol && (
              <p className="text-xs text-destructive">{errors.symbol}</p>
            )}
          </div>

          {/* 수량 */}
          <div className="space-y-1">
            <label htmlFor="holding-quantity" className="text-sm font-medium">
              수량
            </label>
            <input
              id="holding-quantity"
              name="quantity"
              data-testid="holding-quantity"
              type="number"
              step="any"
              min="0"
              value={form.quantity}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, quantity: e.target.value }))
              }
              placeholder="0.001"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            />
            {errors.quantity && (
              <p className="text-xs text-destructive">{errors.quantity}</p>
            )}
          </div>

          {/* 평단가 */}
          <div className="space-y-1">
            <label htmlFor="holding-avg-cost" className="text-sm font-medium">
              평균 매입가
            </label>
            <input
              id="holding-avg-cost"
              name="avg_cost"
              data-testid="holding-avg-cost"
              type="number"
              step="any"
              min="0"
              value={form.avgCost}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, avgCost: e.target.value }))
              }
              placeholder="50000"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            />
            {errors.avgCost && (
              <p className="text-xs text-destructive">{errors.avgCost}</p>
            )}
          </div>

          {/* 통화 선택 */}
          <div className="space-y-1">
            <label htmlFor="holding-currency" className="text-sm font-medium">
              통화
            </label>
            <select
              id="holding-currency"
              value={form.currency}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  currency: e.target.value as "KRW" | "USD" | "USDT",
                }))
              }
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            >
              <option value="KRW">KRW</option>
              <option value="USD">USD</option>
              <option value="USDT">USDT</option>
            </select>
          </div>

          {mutation.isError && (
            <p className="text-xs text-destructive">
              저장 중 오류가 발생했습니다. 다시 시도해 주세요.
            </p>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
            >
              취소
            </Button>
            <Button
              type="submit"
              data-testid="holding-submit"
              disabled={mutation.isPending}
            >
              {mutation.isPending ? "저장 중..." : "추가"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
