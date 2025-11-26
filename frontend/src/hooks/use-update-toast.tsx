import { relaunch } from "@tauri-apps/plugin-process";
import { check, type DownloadEvent } from "@tauri-apps/plugin-updater";
import { useCallback } from "react";
import { toast } from "sonner";

export function useUpdateToast() {
  const downloadAndInstallUpdate = useCallback(
    async (update: Awaited<ReturnType<typeof check>>) => {
      if (!update) return;

      let contentLength: number | undefined;
      let downloaded = 0;
      let progressToastId: string | number | undefined;

      try {
        await update.downloadAndInstall((event: DownloadEvent) => {
          switch (event.event) {
            case "Started":
              contentLength = event.data.contentLength;
              progressToastId = toast.loading("Downloading update... 0%");
              break;

            case "Progress":
              downloaded += event.data.chunkLength;
              if (contentLength && progressToastId) {
                const percentage = Math.min(
                  Math.round((downloaded / contentLength) * 100),
                  100,
                );
                toast.loading(`Downloading update... ${percentage}%`, {
                  id: progressToastId,
                });
              }
              break;

            case "Finished":
              if (progressToastId) {
                toast.dismiss(progressToastId);
              }
              // Show toast with relaunch or later options
              toast.success("Update installed successfully!", {
                description: "The app needs to restart to apply the update.",
                action: {
                  label: "Relaunch",
                  onClick: async () => {
                    await relaunch();
                  },
                },
                cancel: {
                  label: "Later",
                  onClick: () => toast.dismiss(),
                },
                duration: Infinity,
                icon: null,
              });
              break;
          }
        });
      } catch (downloadError) {
        toast.dismiss(progressToastId);
        toast.error(
          `Failed to download update: ${JSON.stringify(downloadError)}`,
        );
      }
    },
    [],
  );

  const checkAndUpdate = useCallback(async () => {
    const checkToastId = toast.loading("Checking for updates...");

    try {
      const update = await check();

      if (!update) {
        toast.dismiss(checkToastId);
        toast.success("You are using the latest version");
        return;
      }

      toast.dismiss(checkToastId);

      // Show toast asking user to install
      const installToastId = toast.info("Update available", {
        description: `A new version (${update.version}) is available. Would you like to install it now?`,
        action: {
          label: "Install",
          onClick: async () => {
            toast.dismiss(installToastId);
            await downloadAndInstallUpdate(update);
          },
        },
        cancel: {
          label: "Later",
          onClick: () => toast.dismiss(installToastId),
        },
        duration: Infinity,
        icon: null,
      });
    } catch (error) {
      toast.dismiss(checkToastId);
      toast.error(`Failed to check for updates: ${JSON.stringify(error)}`);
    }
  }, [downloadAndInstallUpdate]);

  const checkForUpdatesSilent = useCallback(async () => {
    try {
      const update = await check();

      if (!update) {
        return;
      }

      // Show toast asking user to install
      const installToastId = toast.info("Update available", {
        description: `A new version (${update.version}) is available. Would you like to install it now?`,
        action: {
          label: "Install",
          onClick: async () => {
            toast.dismiss(installToastId);
            await downloadAndInstallUpdate(update);
          },
        },
        cancel: {
          label: "Later",
          onClick: () => toast.dismiss(installToastId),
        },
        duration: Infinity,
        icon: null,
      });
    } catch {
      // Silently fail for auto checks
    }
  }, [downloadAndInstallUpdate]);

  return { checkAndUpdate, checkForUpdatesSilent };
}
