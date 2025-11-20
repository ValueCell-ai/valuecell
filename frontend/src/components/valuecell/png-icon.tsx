import { useState } from "react";
import { cn } from "@/lib/utils";

export interface PngIconProps {
  src: string;
  alt?: string;
  className?: string;
  callback?: string;
}

/**
 * Simple PNG Icon component using imported PNG assets
 */
export function PngIcon({ src, alt = "", className, callback }: PngIconProps) {
  const [imgSrc, setImgSrc] = useState(src);

  return (
    <img
      src={imgSrc}
      alt={alt}
      onError={() => {
        callback && setImgSrc(callback);
      }}
      className={cn("size-4 object-contain", className)}
    />
  );
}

export default PngIcon;
