import { AnimatePresence, motion } from "framer-motion";
import type React from "react";
import { useEffect, useState } from "react";
import { useBackendHealth } from "@/api/system";
import ValuecellLogo from "@/assets/png/logo/valuecell-logo.webp";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

export function BackendHealthCheck({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isError, refetch, isSuccess } = useBackendHealth();
  const [showError, setShowError] = useState(false);
  const [progress, setProgress] = useState(0);

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

  // Fake progress bar logic
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (showError) {
      interval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 99) return prev;

          // Dynamic increment logic to simulate realistic loading
          const r = Math.random();
          let increment = 0;

          if (r < 0.1) {
            // 10% chance of "stall" (network delay simulation)
            increment = 0.02;
          } else if (r > 0.9) {
            // 10% chance of "jump" (fast processing)
            increment = 0.8;
          } else {
            // Normal variance: random between 0.1 and 0.4
            // Average is roughly 0.25, keeping total time around 40s
            increment = 0.1 + Math.random() * 0.3;
          }

          return prev + increment;
        });
      }, 100);
    }
    return () => clearInterval(interval);
  }, [showError]);

  if (isSuccess && !showError) {
    return <>{children}</>;
  }

  return (
    <AnimatePresence>
      {showError && (
        <motion.div
          initial={{ opacity: 0.6 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0.6 }}
          transition={{ duration: 0.8, ease: "easeInOut" }}
          className="fixed inset-0 z-9999 flex flex-col items-center justify-center bg-background/80 p-4 text-center"
        >
          <div className="relative flex flex-col items-center justify-center space-y-8 p-8">
            {/* Logo Section with Glow Effect */}
            <motion.div
              animate={{
                scale: [1, 1.1, 1],
                opacity: [0.3, 0.6, 0.3],
              }}
              transition={{
                duration: 4,
                repeat: Number.POSITIVE_INFINITY,
                ease: "easeInOut",
              }}
              className="-z-10 absolute inset-0 rounded-full bg-primary/20 blur-3xl"
            />
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 100, damping: 20 }}
              className="relative z-10"
            >
              <img
                src={ValuecellLogo}
                alt="Valuecell Logo"
                className="size-52 object-contain drop-shadow-2xl"
              />
            </motion.div>

            {/* Text Content */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2, duration: 0.5 }}
              className="space-y-4"
            >
              <h2 className="font-extrabold text-4xl text-foreground tracking-tight">
                Loading Resources
              </h2>
              <p className="text-lg text-muted-foreground leading-relaxed">
                Please wait while we prepare the application environment...
              </p>
            </motion.div>

            {/* Progress Bar & Status */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.4, duration: 0.5 }}
              className="w-full space-y-4"
            >
              <div className="max-w-lg space-y-2">
                <Progress value={progress} className="h-2 w-full bg-muted/50" />
                <div className="flex justify-between font-medium text-muted-foreground text-xs uppercase tracking-wider">
                  <span>Loading</span>
                  <span>{Math.round(progress)}%</span>
                </div>
              </div>

              <Button
                size="lg"
                onClick={() => {
                  setProgress(0);
                  refetch();
                }}
                className="min-w-[160px] cursor-pointer rounded-full shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl"
              >
                Reload Resources
              </Button>
            </motion.div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
