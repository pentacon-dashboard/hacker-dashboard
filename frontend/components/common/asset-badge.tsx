"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useLocale } from "@/lib/i18n/locale-provider";

export type AssetClass = "stock" | "crypto" | "fx" | "macro" | string;

interface AssetBadgeProps {
  assetClass: AssetClass;
  className?: string;
}

const ASSET_LABEL_KEY: Record<string, string> = {
  stock: "symbol.assetClass.stock",
  crypto: "symbol.assetClass.crypto",
  fx: "symbol.assetClass.fx",
  macro: "common.macro",
};

const ASSET_STYLE: Record<string, string> = {
  stock: "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800",
  crypto: "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-800",
  fx: "bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-800",
  macro: "bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700",
};

export function AssetBadge({ assetClass, className }: AssetBadgeProps) {
  const { t } = useLocale();
  const key = ASSET_LABEL_KEY[assetClass];
  const label = key ? t(key) : assetClass.toUpperCase();
  const style = ASSET_STYLE[assetClass] ?? ASSET_STYLE["macro"];

  return (
    <Badge
      variant="outline"
      className={cn(style, "text-xs font-medium", className)}
      aria-label={`${t("common.assetClass")}: ${label}`}
    >
      {label}
    </Badge>
  );
}
