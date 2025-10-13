import type { OverlayScrollbars } from "overlayscrollbars";
import {
  OverlayScrollbarsComponent,
  type OverlayScrollbarsComponentProps,
} from "overlayscrollbars-react";
import { useCallback, useEffect, useRef } from "react";

interface ScrollContainerProps extends OverlayScrollbarsComponentProps {
  children: React.ReactNode;
  /**
   * Whether to automatically scroll to bottom when content changes.
   * Only scrolls if user is already at/near the bottom (smart scroll).
   * @default false
   */
  autoScrollToBottom?: boolean;
}

function ScrollContainer({
  children,
  autoScrollToBottom = false,
  ...props
}: ScrollContainerProps) {
  const osInstanceRef = useRef<OverlayScrollbars | null>(null);
  const wasNearBottomRef = useRef(true);

  // Check if user is at/near bottom of scroll container
  const isNearBottom = useCallback(() => {
    const viewport = osInstanceRef.current?.elements().viewport;
    if (!viewport) return true; // Default to true if no viewport yet
    const { scrollTop, scrollHeight, clientHeight } = viewport;
    const threshold = 50; // 50px threshold for "near bottom"
    return scrollHeight - scrollTop - clientHeight < threshold;
  }, []);

  // Track scroll position before content updates
  useEffect(() => {
    if (!autoScrollToBottom) return;

    const instance = osInstanceRef.current;
    if (!instance) return;

    const viewport = instance.elements().viewport;
    if (!viewport) return;

    // Update ref whenever scroll position changes
    const handleScroll = () => {
      wasNearBottomRef.current = isNearBottom();
    };

    viewport.addEventListener("scroll", handleScroll);
    return () => {
      viewport.removeEventListener("scroll", handleScroll);
    };
  }, [autoScrollToBottom, isNearBottom]);

  // Auto-scroll when children change, if user was near bottom
  // biome-ignore lint/correctness/useExhaustiveDependencies: children is used to trigger the effect when it changes
  useEffect(() => {
    if (!autoScrollToBottom) return;

    const instance = osInstanceRef.current;
    if (!instance) return;

    // Only scroll if user was near bottom before content update
    if (wasNearBottomRef.current) {
      const viewport = instance.elements().viewport;
      if (viewport) {
        // Scroll to bottom smoothly
        viewport.scrollTo({
          top: viewport.scrollHeight,
          behavior: "smooth",
        });
      }
    }
  }, [autoScrollToBottom, children]);

  return (
    <OverlayScrollbarsComponent
      defer
      options={{ scrollbars: { autoHide: "leave", autoHideDelay: 100 } }}
      events={{
        initialized: (instance) => {
          osInstanceRef.current = instance;
        },
        destroyed: () => {
          osInstanceRef.current = null;
        },
      }}
      {...props}
    >
      {children}
    </OverlayScrollbarsComponent>
  );
}

export default ScrollContainer;
