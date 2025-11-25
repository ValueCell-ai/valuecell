import { isTauri } from "@tauri-apps/api/core";
import { useEffect, useRef } from "react";
import { useUpdateToast } from "@/hooks/use-update-toast";

const CHECK_INTERVAL_MS = 60 * 60 * 1000; // Check every hour
const INITIAL_DELAY_MS = 5 * 1000; // Wait 5 seconds after app start

export function AutoUpdateCheck() {
  const { checkForUpdatesSilent } = useUpdateToast();
  const checkIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!isTauri()) return;

    // Initial check after delay
    const initialTimer = setTimeout(() => {
      checkForUpdatesSilent();
    }, INITIAL_DELAY_MS);

    // Set up periodic checks
    checkIntervalRef.current = setInterval(() => {
      checkForUpdatesSilent();
    }, CHECK_INTERVAL_MS);

    return () => {
      clearTimeout(initialTimer);
      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
      }
    };
  }, [checkForUpdatesSilent]);

  return null;
}
