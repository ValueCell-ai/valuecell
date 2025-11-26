import { create } from "zustand";
import { createJSONStorage, devtools, persist } from "zustand/middleware";
import { useShallow } from "zustand/shallow";
import type { SystemInfo } from "@/types/system";
import { TauriStoreState } from "./plugin/tauri-store-state";

const STORAGE_KEY = "valuecell-system-store";

interface SystemStoreState extends SystemInfo {
  setSystemInfo: (info: Partial<SystemInfo>) => void;
}

const INITIAL_SYSTEM_INFO: SystemInfo = {
  client_id: "",
  user_token: "",
};

const store = new TauriStoreState(STORAGE_KEY);
await store.init();

export const useSystemStore = create<SystemStoreState>()(
  devtools(
    persist(
      (set) => ({
        ...INITIAL_SYSTEM_INFO,
        setSystemInfo: (info) => set((state) => ({ ...state, ...info })),
      }),
      {
        name: STORAGE_KEY,
        storage: createJSONStorage(() => store),
      },
    ),
    { name: "SystemStore", enabled: import.meta.env.DEV },
  ),
);

export const useSystemInfo = () => useSystemStore(useShallow((state) => state));
