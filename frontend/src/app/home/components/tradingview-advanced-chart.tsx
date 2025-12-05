import { memo, useEffect, useMemo, useRef } from "react";

type Props = {
  ticker: string;
  mappingUrl?: string;
  interval?: string;
  minHeight?: number;
  theme?: "light" | "dark";
  colors?: { upColor: string; downColor: string };
  locale?: string;
  timezone?: string;
};

function TradingViewAdvancedChart({
  ticker,
  mappingUrl,
  interval = "D",
  minHeight = 420,
  theme = "light",
  colors,
  locale = "en",
  timezone = "UTC",
}: Props) {
  const symbolMapRef = useRef<Record<string, string> | null>(null);

  useEffect(() => {
    if (!mappingUrl) return;
    let cancelled = false;
    fetch(mappingUrl)
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((json) => {
        if (!cancelled) symbolMapRef.current = json || {};
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [mappingUrl]);

  const tvSymbol = useMemo(() => {
    const m = symbolMapRef.current;
    if (m && typeof m === "object" && ticker in m) {
      const v = m[ticker];
      if (typeof v === "string" && v.length > 0) return v;
    }
    if (ticker.includes(":")) return ticker;
    return ticker;
  }, [ticker, mappingUrl]);

  const containerId = useMemo(
    () => `tv_${tvSymbol.replace(/[^A-Za-z0-9_]/g, "_")}_${interval}`,
    [tvSymbol, interval],
  );

  const containerRef = useRef<HTMLDivElement | null>(null);

  const loadTradingView = () => {
    const w = window as any;
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
      const current = containerRef.current as any;
      const widget = current?.__tv_widget__;
      if (widget && typeof widget.remove === "function") {
        try {
          widget.remove();
        } catch {}
      }
      if (containerRef.current) {
        (containerRef.current as any).__tv_widget__ = null;
        containerRef.current.innerHTML = "";
      }
    };

    cleanup();
    if (!tvSymbol) return;

    loadTradingView().then(() => {
      const w = window as any;
      if (cancelled || !containerRef.current || !w.TradingView) return;

      const overrides = colors
        ? {
            "mainSeriesProperties.candleStyle.upColor": colors.upColor,
            "mainSeriesProperties.candleStyle.downColor": colors.downColor,
            "mainSeriesProperties.candleStyle.borderUpColor": colors.upColor,
            "mainSeriesProperties.candleStyle.borderDownColor":
              colors.downColor,
            "mainSeriesProperties.candleStyle.wickUpColor": colors.upColor,
            "mainSeriesProperties.candleStyle.wickDownColor": colors.downColor,
            "mainSeriesProperties.candleStyle.drawWick": true,
            "mainSeriesProperties.candleStyle.drawBorder": true,
          }
        : {
            "mainSeriesProperties.candleStyle.drawWick": true,
            "mainSeriesProperties.candleStyle.drawBorder": true,
          };

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
        overrides,
      });

      const current = containerRef.current as any;
      if (current) current.__tv_widget__ = widget;
    });

    return () => {
      cancelled = true;
      cleanup();
    };
  }, [tvSymbol, interval, theme, colors, locale, timezone]);

  return (
    <div className="w-full" style={{ height: minHeight }}>
      <div id={containerId} ref={containerRef} className="h-full" />
    </div>
  );
}

export default memo(TradingViewAdvancedChart);
