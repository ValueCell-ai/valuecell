import { invoke, isTauri } from "@tauri-apps/api/core";
import { arch, platform, version } from "@tauri-apps/plugin-os";
import { VALUECELL_BACKEND_URL } from "@/constants/api";
import { useSystemStore } from "@/store/system-store";
import { apiClient } from "./api-client";

export interface TrackingEvents {
  login: undefined;
  logout: undefined;
  use: {
    agent_name: string;
  };
}
declare module "react" {
  interface HTMLAttributes<T> extends DOMAttributes<T> {
    "data-track"?: keyof TrackingEvents;
    "data-track-params"?: string; // 必须是 JSON 字符串
  }
}

interface TrackerConfig {
  endpoint: string;
}

interface TrackingParams {
  user_id: string;
  client_id: string;
  os: string;
  [key: string]: unknown;
}

class Tracker {
  private config: TrackerConfig;
  private params: TrackingParams;

  constructor(config: TrackerConfig) {
    this.config = config;
    this.params = {
      user_id: useSystemStore.getState().id,
      client_id: "",
      os: "",
    };
    void this.init();
  }

  private async init() {
    try {
      const clientId = await invoke<string>("get_client_id");
      const systemInfo = JSON.stringify(
        await {
          platform: await platform(),
          arch: await arch(),
          version: await version(),
        },
      );

      this.params = {
        ...this.params,
        client_id: clientId,
        os: systemInfo,
      };
    } catch (error) {
      console.warn("Failed to initialize tracker:", JSON.stringify(error));
    }
  }

  public send<K extends keyof TrackingEvents>(
    event: K,
    params?: TrackingEvents[K],
  ) {
    if (!isTauri()) return;

    const payload = {
      event,
      ...this.params,
      ...params,
    };

    // if (navigator.sendBeacon) {
    //   const blob = new Blob([JSON.stringify(payload)], {
    //     type: "application/json",
    //   });
    //   navigator.sendBeacon(this.config.endpoint, blob);
    // } else {
    apiClient
      .post(this.config.endpoint, payload, {
        keepalive: true,
        wrapError: false,
      })
      .catch((error) => {
        console.warn("Failed to send tracking event:", JSON.stringify(error));
      });
    // }

    if (import.meta.env.DEV) {
      console.log(
        `%c[Tracker] ${event}`,
        "color: #20b2aa; font-weight: bold",
        payload,
      );
    }
  }
}

const tracker = new Tracker({
  endpoint: `${VALUECELL_BACKEND_URL}/analytics/event`,
});

export const withTrack = <T extends keyof TrackingEvents>(
  event: T,
  params?: TrackingEvents[T],
) => {
  return {
    "data-track": event,
    "data-track-params": JSON.stringify(params ?? {}),
  };
};

export { tracker, type TrackerConfig, type TrackingParams };
