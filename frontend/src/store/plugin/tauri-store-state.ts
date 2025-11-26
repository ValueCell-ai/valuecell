import { load, type Store } from "@tauri-apps/plugin-store";
import type { StateStorage } from "zustand/middleware";
import { debounce } from "@/hooks/use-debounce";

export class TauriStoreState implements StateStorage {
  private store: Store | null = null;
  private debouncedSave: (() => void) | null = null;

  constructor(public storeName: string) {}

  async init() {
    this.store = await load(this.storeName);
    if (!this.store) {
      throw new Error(`Failed to load store: ${this.storeName}`);
    }

    this.debouncedSave = debounce(() => this.store?.save(), 1 * 1000) ?? null;
  }

  async getItem(name: string) {
    const res = await this.store?.get<string>(name);
    return res ?? null;
  }

  async setItem(name: string, value: string) {
    await this.store?.set(name, value);
    this.debouncedSave?.();
  }

  async removeItem(name: string) {
    await this.store?.delete(name);
    this.debouncedSave?.();
  }
}
