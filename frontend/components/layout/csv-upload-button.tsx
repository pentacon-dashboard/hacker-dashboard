"use client";

import Link from "next/link";
import { Upload } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { useLocale } from "@/lib/i18n/locale-provider";

export function CsvUploadButton() {
  const { t } = useLocale();

  return (
    <Link
      href="/upload"
      className={buttonVariants({
        variant: "outline",
        size: "sm",
        className: "h-8 gap-1.5 px-2.5 text-xs",
      })}
      aria-label={t("header.csvUploadLabel")}
      data-testid="csv-upload-button"
    >
      <Upload className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span className="hidden sm:inline">{t("header.csvUpload")}</span>
    </Link>
  );
}
