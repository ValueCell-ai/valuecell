import { create } from "zustand";
import { createJSONStorage, devtools, persist } from "zustand/middleware";
import { useShallow } from "zustand/shallow";
import type { SystemInfo } from "@/types/system";
import { TauriStoreState } from "./plugin/tauri-store-state";

const STORAGE_KEY = "valuecell-system-store";

interface SystemStoreState extends SystemInfo {
  setSystemInfo: (info: Partial<SystemInfo>) => void;
  clearSystemInfo: () => void;
}

const INITIAL_SYSTEM_INFO: SystemInfo = {
  access_token: "",
  refresh_token: "",
  id: "",
  email: "",
  name: "",
  avatar: "",
  created_at: "",
  updated_at: "",
};

const store = new TauriStoreState(STORAGE_KEY);
await store.init();

export const useSystemStore = create<SystemStoreState>()(
  devtools(
    persist(
      (set) => ({
        ...INITIAL_SYSTEM_INFO,
        setSystemInfo: (info) => set((state) => ({ ...state, ...info })),
        clearSystemInfo: () => set(INITIAL_SYSTEM_INFO),
      }),
      {
        name: STORAGE_KEY,
        storage: createJSONStorage(() => store),
      },
    ),
    { name: "SystemStore", enabled: import.meta.env.DEV },
  ),
);

export const useSystemInfo = () =>
  useSystemStore(
    useShallow((state) => ({
      id: state.id,
      email: state.email,
      name: state.name,
      avatar: state.avatar,
      created_at: state.created_at,
      updated_at: state.updated_at,
    })),
  );

export const useSystemAccessToken = () =>
  useSystemStore((state) => state.access_token);

export const useIsLoggedIn = () =>
  useSystemStore(useShallow((state) => !!state.id && !!state.access_token));
