import { memo } from "react";
import { cn } from "@/lib/utils";

export interface SvgIconProps {
  name: string;
  className?: string;
}

/**
 * Simple SVG Icon component using optimized SVG sprites
 */
export function SvgIcon({ name, className }: SvgIconProps) {
  return (
    <svg className={cn("size-full", className)}>
      <use href={`#${name}`} />
    </svg>
  );
}

export default memo(SvgIcon);
