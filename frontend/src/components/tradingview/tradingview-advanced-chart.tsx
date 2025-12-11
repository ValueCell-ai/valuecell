import { memo, useEffect, useMemo, useRef } from "react";
import defaultMap from "./tv-symbol-map.json";

interface TradingViewAdvancedChartProps {
  ticker: string;
  mappingUrl?: string;
  interval?: string;
  minHeight?: number;
  theme?: "light" | "dark";
  locale?: string;
  timezone?: string;
}

interface TradingViewWindow extends Window {
  TradingView?: {
    widget: new (
      config: Record<string, unknown>,
    ) => {
      remove?: () => void;
    };
  };
  __tvScriptPromise?: Promise<void>;
}

interface TradingViewContainer extends HTMLDivElement {
  __tv_widget__?: {
    remove?: () => void;
  } | null;
}

function TradingViewAdvancedChart({
  ticker,
  mappingUrl,
  interval = "D",
  minHeight = 420,
  theme = "light",
  locale = "en",
  timezone = "UTC",
}: TradingViewAdvancedChartProps) {
  const symbolMapRef = useRef<Record<string, string>>(
    defaultMap as Record<string, string>,
  );

  useEffect(() => {
    if (!mappingUrl) return;
    let cancelled = false;
    fetch(mappingUrl)
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((json) => {
        if (!cancelled)
          symbolMapRef.current = (json || {}) as Record<string, string>;
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [mappingUrl]);

  const tvSymbol = useMemo(() => {
    const t = ticker;
    if (typeof t === "string" && t.includes(":")) {
      const [ex, sym] = t.split(":");
      const exUpper = ex.toUpperCase();
      if (exUpper === "HKEX") {
        const norm = (sym ?? "").replace(/^0+/, "") || "0";
        return `${exUpper}:${norm}`;
      }
    }
    const m = symbolMapRef.current;
    if (m && typeof m === "object" && t in m) {
      const v = m[t];
      if (typeof v === "string" && v.length > 0) return v;
    }
    return t;
  }, [ticker]);

  const containerId = useMemo(
    () => `tv_${tvSymbol.replace(/[^A-Za-z0-9_]/g, "_")}_${interval}`,
    [tvSymbol, interval],
  );

  const containerRef = useRef<TradingViewContainer | null>(null);

  const loadTradingView = () => {
    const w = window as TradingViewWindow;
    if (w.TradingView) return Promise.resolve();
    if (w.__tvScriptPromise) return w.__tvScriptPromise;
    w.__tvScriptPromise = new Promise<void>((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://s3.tradingview.com/tv.js";
      script.async = true;
      script.onload = () => resolve();
      script.onerror = reject;
      document.head.appendChild(script);
    });
    return w.__tvScriptPromise;
  };

  useEffect(() => {
    let cancelled = false;

    const cleanup = () => {
      const current = containerRef.current;
      const widget = current?.__tv_widget__;
      if (widget && typeof widget.remove === "function") {
        try {
          widget.remove();
        } catch {}
      }
      if (containerRef.current) {
        containerRef.current.__tv_widget__ = null;
        containerRef.current.innerHTML = "";
      }
    };

    cleanup();
    if (!tvSymbol) return;

    loadTradingView().then(() => {
      const w = window as TradingViewWindow;
      if (cancelled || !containerRef.current || !w.TradingView) return;

      const widget = new w.TradingView.widget({
        container_id: containerId,
        symbol: tvSymbol,
        interval,
        timezone,
        theme,
        locale,
        autosize: true,
        hide_top_toolbar: false,
        hide_side_toolbar: false,
        hide_bottom_toolbar: false,
        allow_symbol_change: false,
        details: true,
      });

      const current = containerRef.current;
      if (current) current.__tv_widget__ = widget;
    });

    return () => {
      cancelled = true;
      cleanup();
    };
  }, [tvSymbol, interval, theme, locale, timezone, containerId]);

  return (
    <div className="w-full" style={{ height: minHeight }}>
      <div id={containerId} ref={containerRef} className="h-full" />
    </div>
  );
}

export default memo(TradingViewAdvancedChart);
