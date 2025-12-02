import { getCurrentWindow } from "@tauri-apps/api/window";
import { onOpenUrl } from "@tauri-apps/plugin-deep-link";
import { openUrl } from "@tauri-apps/plugin-opener";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { getUserInfo } from "@/api/system";
import { Logo } from "@/assets/svg";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { tracker } from "@/lib/tracker";
import { useSystemStore } from "@/store/system-store";
import CloseButton from "../button/close-button";
import SvgIcon from "../icon/svg-icon";
import ScrollContainer from "../scroll/scroll-container";

type PendingAction = "gmail" | "apple";

export interface AppLoginModalProps {
  children?: React.ReactNode;
}

export default function AppLoginModal({ children }: AppLoginModalProps) {
  const [open, setOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(
    null,
  );

  const timeoutRef = useRef<number | undefined>(undefined);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  const setSystemInfo = useSystemStore((state) => state.setSystemInfo);

  const clearLoginHandlers = useCallback(() => {
    if (timeoutRef.current !== undefined) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = undefined;
    }

    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
    }

    setPendingAction(null);
  }, []);

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      clearLoginHandlers();
    }

    setOpen(nextOpen);
  };

  const handleLogin = async (provider: PendingAction) => {
    clearLoginHandlers();
    setPendingAction(provider);

    try {
      await openUrl(`https://valuecell.ai/login?provider=${provider}`);

      const unsubscribe = await onOpenUrl(async (urls) => {
        clearLoginHandlers();

        if (urls.length > 0) {
          const app_window = getCurrentWindow();
          if (await app_window.isMinimized()) {
            await app_window.unminimize();
          }
          await app_window.setFocus();
          const params = new URLSearchParams(urls[0].split("?")[1]);
          const access_token = params.get("access_token");
          const refresh_token = params.get("refresh_token");
          if (access_token && refresh_token) {
            const userInfo = await getUserInfo(access_token);

            if (userInfo) {
              setSystemInfo({
                access_token,
                refresh_token,
                ...userInfo,
              });
            }

            tracker.send("login");

            setOpen(false);
          }
        }
      });

      unsubscribeRef.current = unsubscribe;

      timeoutRef.current = window.setTimeout(
        () => {
          clearLoginHandlers();
          toast.error("Login timed out, please try again.");
        },
        2 * 60 * 1000,
      );
    } catch (error) {
      toast.error(
        `Failed to login with ${provider}, info: ${JSON.stringify(error)}`,
      );
    }
  };

  useEffect(() => {
    return () => {
      clearLoginHandlers();
    };
  }, [clearLoginHandlers]);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent
        className="flex max-h-[90vh] min-h-96 flex-col"
        showCloseButton={false}
        aria-describedby={undefined}
      >
        <DialogTitle className="flex items-center justify-between">
          Sign in
          <DialogClose asChild>
            <CloseButton />
          </DialogClose>
        </DialogTitle>

        <ScrollContainer className="mt-10">
          <div className="flex flex-col items-center gap-3 text-center">
            <SvgIcon
              name={Logo}
              className="size-14 rounded-full bg-black p-2.5 text-white"
            />
            <p className="font-medium text-3xl text-gray-950">ValueCell</p>
            <p className="font-medium text-gray-500 text-sm">
              The first open-source platform for financial agents
            </p>
          </div>

          <div className="mt-10 flex flex-col gap-4 px-4 pb-4">
            <Button
              variant="outline"
              className="relative bg-gray-50 py-6 text-base focus-visible:ring-gray-200"
              onClick={() => handleLogin("gmail")}
              disabled={pendingAction !== null}
            >
              <svg
                className="-translate-y-1/2 absolute top-1/2 left-4"
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
              >
                <path
                  d="M3.21121 7.67735C3.21181 7.19253 3.29133 6.71104 3.44664 6.25177L0.804273 4.27539C0.275388 5.3308 0 6.49504 0 7.67555C0 8.85607 0.275388 10.0203 0.804273 11.0757L3.4452 9.09646C3.29112 8.63917 3.21234 8.1599 3.21193 7.67735"
                  fill="#FBBC05"
                />
                <path
                  d="M7.85466 3.1395C8.90549 3.13673 9.92561 3.49371 10.7454 4.15109L13.03 1.91912C12.1221 1.13883 11.0497 0.573842 9.89275 0.266401C8.73582 -0.0410395 7.52437 -0.0829818 6.34895 0.14371C5.17353 0.370401 4.06456 0.859862 3.10495 1.5755C2.14533 2.29114 1.3599 3.21444 0.807373 4.27637L3.45118 6.25275C3.76674 5.33805 4.36165 4.54558 5.15189 3.98723C5.94214 3.42887 6.88781 3.13285 7.85538 3.14094"
                  fill="#EA4335"
                />
                <path
                  d="M7.85538 12.2134C6.88764 12.2214 5.9418 11.9254 5.15133 11.3671C4.36086 10.8088 3.76566 10.0163 3.44974 9.10156L0.807373 11.0779C1.46984 12.3744 2.47989 13.461 3.72457 14.2163C4.96926 14.9716 6.3995 15.3657 7.85538 15.3547C9.73948 15.3754 11.5637 14.6931 12.9716 13.441L10.4625 11.5423C9.67218 12.0034 8.76932 12.2357 7.85466 12.2134"
                  fill="#34A853"
                />
                <path
                  d="M15.3481 7.67634C15.3412 7.20575 15.2814 6.73744 15.1696 6.28027H7.85229V9.24664H12.0642C11.9718 9.7198 11.7814 10.1684 11.5053 10.5636C11.2291 10.9587 10.8734 11.2918 10.4608 11.5413L12.9693 13.4406C13.7524 12.704 14.3694 11.8088 14.7792 10.8148C15.1889 9.82081 15.3819 8.75085 15.3453 7.67634"
                  fill="#4285F4"
                />
              </svg>
              Continue with Google
              {pendingAction === "gmail" && (
                <Spinner className="-translate-y-1/2 absolute top-1/2 right-4" />
              )}
            </Button>
            {/* 
            <Button
              variant="outline"
              className="relative bg-gray-50 py-6 text-base focus-visible:ring-gray-200"
              onClick={() => handleLogin("apple")}
              disabled={pendingAction !== null}
            >
              <svg
                className="-translate-y-1/2 absolute top-1/2 left-4"
                width="14"
                height="17"
                viewBox="0 0 14 17"
                fill="none"
              >
                <path
                  d="M11.0546 8.63573C11.0546 6.61173 12.7412 5.59973 12.8087 5.53226C11.8642 4.11546 10.3799 3.98053 9.84016 3.91306C8.55829 3.77813 7.41136 4.6552 6.73669 4.6552C6.12949 4.6552 5.11749 3.91306 4.03803 3.98053C2.68869 3.98053 1.40683 4.79013 0.664695 6.00453C-0.752104 8.43333 0.327362 12.144 1.74416 14.168C2.41883 15.18 3.22843 16.2595 4.30789 16.192C5.31989 16.1245 5.72469 15.5173 6.93909 15.5173C8.15349 15.5173 8.55829 16.192 9.63776 16.192C10.7172 16.192 11.4594 15.18 12.134 14.2355C12.9436 13.0885 13.2135 12.0091 13.281 11.9416C13.146 11.8741 11.0546 11.0645 11.0546 8.63573ZM8.96309 2.56373C9.50282 1.88907 9.90762 0.944533 9.77269 0C8.96309 0 7.95109 0.539733 7.41136 1.2144C6.87162 1.8216 6.39936 2.76613 6.53429 3.71066C7.47882 3.77813 8.42336 3.2384 8.96309 2.56373Z"
                  fill="#030712"
                />
              </svg>
              Continue with Apple
              {pendingAction === "apple" && (
                <Spinner className="-translate-y-1/2 absolute top-1/2 right-4" />
              )}
            </Button> */}
          </div>
        </ScrollContainer>
      </DialogContent>
    </Dialog>
  );
}
