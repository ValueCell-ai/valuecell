import { AnimatePresence, motion } from "framer-motion";
import { RefreshCw, ServerCrash, WifiOff } from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { useBackendHealth } from "@/api/system";
import { Button } from "@/components/ui/button";

export function BackendHealthCheck({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isError, refetch, isFetching, isSuccess } = useBackendHealth();
  const [showError, setShowError] = useState(false);

  // Debounce showing the error screen to avoid flickering on initial load or brief network blips
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    if (isError) {
      timer = setTimeout(() => setShowError(true), 500);
    } else {
      setShowError(false);
    }
    return () => clearTimeout(timer);
  }, [isError]);

  if (isSuccess && !showError) {
    return <>{children}</>;
  }

  return (
    <>
      {/* We can render children hidden or not at all. 
          If we want to block initialization completely, we don't render children.
          If we want to keep the app mounted but covered, we render children.
          Given the requirement "normal routing requests should not be sent out", 
          we should NOT render children when in error state. 
      */}
      {/* However, for initial load, we might want to show a loading state or just wait.
          If we are in "loading" state (initial fetch), we might want to show a spinner or nothing.
          If we are in "error" state, we show the error screen.
      */}

      <AnimatePresence>
        {showError && (
          <motion.div
            initial={{ opacity: 0, backdropFilter: "blur(0px)" }}
            animate={{ opacity: 1, backdropFilter: "blur(12px)" }}
            exit={{ opacity: 0, backdropFilter: "blur(0px)" }}
            transition={{ duration: 0.5 }}
            className="fixed inset-0 z-9999 flex flex-col items-center justify-center bg-background p-4 text-center"
          >
            <div className="relative flex w-full max-w-md flex-col items-center justify-center space-y-8">
              {/* Animated Icon Container */}
              <div className="relative">
                <motion.div
                  animate={{
                    scale: [1, 1.2, 1],
                    opacity: [0.1, 0.05, 0.1],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                  className="absolute inset-0 rounded-full bg-foreground/10 blur-xl"
                />
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ type: "spring", stiffness: 200, damping: 15 }}
                  className="relative flex h-24 w-24 items-center justify-center rounded-full border border-border bg-background shadow-xl"
                >
                  <ServerCrash className="h-10 w-10 text-foreground" />

                  {/* Orbiting dot */}
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{
                      duration: 3,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                    className="absolute inset-0 rounded-full"
                  >
                    <div className="-translate-x-1/2 -translate-y-1 absolute top-0 left-1/2 h-2.5 w-2.5 rounded-full bg-foreground shadow-[0_0_8px_rgba(0,0,0,0.2)] dark:shadow-[0_0_8px_rgba(255,255,255,0.2)]" />
                  </motion.div>
                </motion.div>
              </div>

              {/* Text Content */}
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="space-y-3"
              >
                <h2 className="font-bold text-3xl text-foreground tracking-tight">
                  Waiting For Service
                </h2>
                <p className="text-lg text-muted-foreground leading-relaxed">
                  The backend is starting or waiting to start. <br />
                  Please wait while we attempt to connect...
                </p>
              </motion.div>

              {/* Status Indicator & Action */}
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.4 }}
                className="flex w-full flex-col items-center gap-4"
              >
                <div className="flex items-center gap-2 rounded-full border border-border bg-muted/30 px-4 py-2 font-medium text-muted-foreground text-sm">
                  {isFetching ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      <span>Attempting to reconnect...</span>
                    </>
                  ) : (
                    <>
                      <WifiOff className="h-3.5 w-3.5" />
                      <span>Connection lost</span>
                    </>
                  )}
                </div>

                <Button
                  size="lg"
                  variant="default"
                  onClick={() => refetch()}
                  className="min-w-[160px] shadow-md transition-all duration-300 hover:shadow-lg"
                >
                  Try Now
                </Button>
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* While loading initially (and not error yet), we might want to show nothing or a splash screen. 
          For now, we'll just render nothing until we have success or error.
      */}
    </>
  );
}
