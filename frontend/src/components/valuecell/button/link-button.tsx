import { openUrl } from "@tauri-apps/plugin-opener";
import type React from "react";
import type { FC } from "react";
import { useTauriInfo } from "@/hooks/use-tauri-info";
import { cn } from "@/lib/utils";

type LinkButtonProps = {
  url: string;
  className?: string;
  children: React.ReactNode;
};

const LinkButton: FC<LinkButtonProps> = ({ className, url, children }) => {
  const { isTauriApp } = useTauriInfo();

  return (
    <button
      type="button"
      className={cn(
        "cursor-pointer text-sm underline underline-offset-4",
        className,
      )}
      onClick={() => (isTauriApp ? openUrl(url) : window.open(url, "_blank"))}
    >
      {children}
    </button>
  );
};

export default LinkButton;
