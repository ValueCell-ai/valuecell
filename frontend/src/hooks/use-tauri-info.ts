import { getVersion } from "@tauri-apps/api/app";
import { isTauri } from "@tauri-apps/api/core";
import { useEffect, useState } from "react";

/**
 * Resolve whether we're running inside a Tauri shell and lazily fetch the app
 * version. Keeping this logic in a hook avoids calling async helpers during
 * render, which breaks React's invariants.
 */
export function useTauriInfo() {
  const [isTauriApp, setIsTauriApp] = useState(false);
  const [appVersion, setAppVersion] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const resolveEnvironment = async () => {
      try {
        const tauri = await isTauri();
        if (cancelled) return;

        setIsTauriApp(tauri);

        if (!tauri) return;

        const version = await getVersion();
        if (!cancelled) {
          setAppVersion(version);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void resolveEnvironment();

    return () => {
      cancelled = true;
    };
  }, []);

  return { isTauriApp, appVersion, isLoading };
}
