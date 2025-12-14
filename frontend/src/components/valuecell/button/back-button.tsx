import { ArrowLeft } from "lucide-react";
import type { ComponentProps } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function BackButton({ className, ...props }: ComponentProps<"button">) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <Button
      className={cn("w-fit cursor-pointer text-neutral-400", className)}
      variant="ghost"
      size="sm"
      onClick={() => navigate(-1)}
      {...props}
    >
      <ArrowLeft className="h-4 w-4" /> {t("common.back")}
    </Button>
  );
}

export default BackButton;
