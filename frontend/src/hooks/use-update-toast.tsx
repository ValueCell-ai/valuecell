import { relaunch } from "@tauri-apps/plugin-process";
import { check, type DownloadEvent } from "@tauri-apps/plugin-updater";
import { useCallback } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

export function useUpdateToast() {
  const { t } = useTranslation();
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
              progressToastId = toast.loading(
                t("updates.toast.downloading", { percentage: 0 }),
              );
              break;

            case "Progress":
              downloaded += event.data.chunkLength;
              if (contentLength && progressToastId) {
                const percentage = Math.min(
                  Math.round((downloaded / contentLength) * 100),
                  100,
                );
                toast.loading(t("updates.toast.downloading", { percentage }), {
                  id: progressToastId,
                });
              }
              break;

            case "Finished":
              if (progressToastId) {
                toast.dismiss(progressToastId);
              }
              // Show toast with relaunch or later options
              toast.success(t("updates.toast.installedTitle"), {
                description: t("updates.toast.installedDesc"),
                action: {
                  label: t("updates.toast.relaunch"),
                  onClick: async () => {
                    await relaunch();
                  },
                },
                cancel: {
                  label: t("updates.toast.later"),
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
          t("updates.toast.downloadFailed", {
            error: JSON.stringify(downloadError),
          }),
        );
      }
    },
    [t],
  );

  const checkAndUpdate = useCallback(async () => {
    const checkToastId = toast.loading(t("updates.toast.checking"));

    try {
      const update = await check();

      if (!update) {
        toast.dismiss(checkToastId);
        toast.success(t("updates.toast.latest"));
        return;
      }

      toast.dismiss(checkToastId);

      // Show toast asking user to install
      const installToastId = toast.info(t("updates.toast.availableTitle"), {
        description: t("updates.toast.availableDesc", {
          version: update.version,
        }),
        action: {
          label: t("updates.toast.install"),
          onClick: async () => {
            toast.dismiss(installToastId);
            await downloadAndInstallUpdate(update);
          },
        },
        cancel: {
          label: t("updates.toast.later"),
          onClick: () => toast.dismiss(installToastId),
        },
        duration: Infinity,
        icon: null,
      });
    } catch (error) {
      toast.dismiss(checkToastId);
      toast.error(
        t("updates.toast.checkFailed", { error: JSON.stringify(error) }),
      );
    }
  }, [downloadAndInstallUpdate, t]);

  const checkForUpdatesSilent = useCallback(async () => {
    try {
      const update = await check();

      if (!update) {
        return;
      }

      // Show toast asking user to install
      const installToastId = toast.info(t("updates.toast.availableTitle"), {
        description: t("updates.toast.availableDesc", {
          version: update.version,
        }),
        action: {
          label: t("updates.toast.install"),
          onClick: async () => {
            toast.dismiss(installToastId);
            await downloadAndInstallUpdate(update);
          },
        },
        cancel: {
          label: t("updates.toast.later"),
          onClick: () => toast.dismiss(installToastId),
        },
        duration: Infinity,
        icon: null,
      });
    } catch {
      // Silently fail for auto checks
    }
  }, [downloadAndInstallUpdate, t]);

  return { checkAndUpdate, checkForUpdatesSilent };
}
