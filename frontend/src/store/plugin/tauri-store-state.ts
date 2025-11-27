import { load, type Store } from "@tauri-apps/plugin-store";
import type { StateStorage } from "zustand/middleware";
import { debounce } from "@/hooks/use-debounce";

const hasBrowserWindow = () => typeof window !== "undefined";

export class TauriStoreState implements StateStorage {
  private store: Store | null = null;
  private debouncedSave: (() => void) | null = null;
  private initialized = false;

  constructor(public storeName: string) {}

  async init() {
    if (this.initialized) {
      return;
    }

    this.initialized = true;

    if (!hasBrowserWindow()) {
      // When server-rendering we skip initializing the Tauri store.
      return;
    }

    const tauriInternals = (
      window as Window & { __TAURI_INTERNALS__?: unknown }
    ).__TAURI_INTERNALS__;

    if (!tauriInternals) {
      // Running in a regular browser; fall back to default persist storage.
      return;
    }

    this.store = await load(this.storeName);
    if (!this.store) {
      throw new Error(`Failed to load store: ${this.storeName}`);
    }

    this.debouncedSave = debounce(() => this.store?.save(), 1 * 1000) ?? null;
  }

  async getItem(name: string) {
    if (!this.store) {
      return null;
    }

    const res = await this.store.get<string>(name);
    return res ?? null;
  }

  async setItem(name: string, value: string) {
    if (!this.store) {
      return;
    }

    await this.store.set(name, value);
    this.debouncedSave?.();
  }

  async removeItem(name: string) {
    if (!this.store) {
      return;
    }

    await this.store.delete(name);
    this.debouncedSave?.();
  }
}
