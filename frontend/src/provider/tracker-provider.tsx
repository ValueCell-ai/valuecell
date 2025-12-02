import { parse } from "best-effort-json-parser";
import { useEffect } from "react";
import { type TrackingEvents, tracker } from "@/lib/tracker";

export const TrackerProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  useEffect(() => {
    const handleGlobalClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement;

      // find the closest tracked element
      const trackedElements = target.closest("[data-track]");

      if (trackedElements) {
        const event = trackedElements.getAttribute(
          "data-track",
        ) as keyof TrackingEvents;

        if (!event) return;

        const params =
          trackedElements.getAttribute("data-track-params") ?? "{}";
        tracker.send(event, parse(params));
      }
    };

    document.addEventListener("click", handleGlobalClick, true);

    return () => {
      document.removeEventListener("click", handleGlobalClick, true);
    };
  }, []);

  return <>{children}</>;
};
