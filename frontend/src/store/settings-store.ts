import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { useShallow } from "zustand/shallow";
import {
  GREEN_BADGE,
  GREEN_COLOR,
  GREEN_GRADIENT,
  NEUTRAL_BADGE,
  NEUTRAL_COLOR,
  NEUTRAL_GRADIENT,
  RED_BADGE,
  RED_COLOR,
  RED_GRADIENT,
} from "@/constants/stock";
import type { StockChangeType } from "@/types/stock";

export type StockColorMode = "GREEN_UP_RED_DOWN" | "RED_UP_GREEN_DOWN";

interface SettingsStoreState {
  stockColorMode: StockColorMode;
  setStockColorMode: (mode: StockColorMode) => void;
}

const INITIAL_STATE = {
  stockColorMode: "GREEN_UP_RED_DOWN" as StockColorMode,
};

/**
 * Global settings store with localStorage persistence
 */
export const useSettingsStore = create<SettingsStoreState>()(
  devtools(
    persist(
      (set) => ({
        ...INITIAL_STATE,
        setStockColorMode: (stockColorMode) => set({ stockColorMode }),
      }),
      {
        name: "valuecell-settings",
      },
    ),
    { name: "SettingsStore", enabled: import.meta.env.DEV },
  ),
);

export const useStockColorMode = () =>
  useSettingsStore(useShallow((s) => s.stockColorMode));

export const useSettingsActions = () =>
  useSettingsStore(
    useShallow((s) => ({
      setStockColorMode: s.setStockColorMode,
    })),
  );

/**
 * Get stock colors based on current color mode setting
 */
export const useStockColors = (): Record<StockChangeType, string> => {
  const colorMode = useStockColorMode();
  if (colorMode === "RED_UP_GREEN_DOWN") {
    return {
      positive: RED_COLOR,
      negative: GREEN_COLOR,
      neutral: NEUTRAL_COLOR,
    };
  }
  return {
    positive: GREEN_COLOR,
    negative: RED_COLOR,
    neutral: NEUTRAL_COLOR,
  };
};

/**
 * Get stock gradient colors based on current color mode setting
 */
export const useStockGradientColors = (): Record<
  StockChangeType,
  [string, string]
> => {
  const colorMode = useStockColorMode();
  if (colorMode === "RED_UP_GREEN_DOWN") {
    return {
      positive: RED_GRADIENT,
      negative: GREEN_GRADIENT,
      neutral: NEUTRAL_GRADIENT,
    };
  }
  return {
    positive: GREEN_GRADIENT,
    negative: RED_GRADIENT,
    neutral: NEUTRAL_GRADIENT,
  };
};

/**
 * Get stock badge colors based on current color mode setting
 */
export const useStockBadgeColors = (): Record<
  StockChangeType,
  { bg: string; text: string }
> => {
  const colorMode = useStockColorMode();
  if (colorMode === "RED_UP_GREEN_DOWN") {
    return {
      positive: RED_BADGE,
      negative: GREEN_BADGE,
      neutral: NEUTRAL_BADGE,
    };
  }
  return {
    positive: GREEN_BADGE,
    negative: RED_BADGE,
    neutral: NEUTRAL_BADGE,
  };
};
