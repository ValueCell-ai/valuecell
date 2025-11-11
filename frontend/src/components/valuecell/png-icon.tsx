import { cn } from "@/lib/utils";

export interface PngIconProps {
  src: string;
  alt?: string;
  className?: string;
}

/**
 * Simple PNG Icon component using imported PNG assets
 */
export function PngIcon({ src, alt = "", className }: PngIconProps) {
  return (
    <img
      src={src}
      alt={alt}
      className={cn("size-4 object-contain", className)}
    />
  );
}

export default PngIcon;
