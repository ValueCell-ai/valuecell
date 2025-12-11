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
  const containerRef = useRef<HTMLDivElement | null>(null);
  const scriptRef = useRef<HTMLScriptElement | null>(null);

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

  useEffect(() => {
    if (!containerRef.current || !tvSymbol) return;

    if (scriptRef.current && containerRef.current.contains(scriptRef.current)) {
      containerRef.current.removeChild(scriptRef.current);
      scriptRef.current = null;
    }
    containerRef.current.innerHTML = "";

    const script = document.createElement("script");
    script.type = "text/javascript";
    script.async = true;
    script.src =
      "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.innerHTML = JSON.stringify({
      allow_symbol_change: true,
      calendar: false,
      details: false,
      hide_side_toolbar: true,
      hide_top_toolbar: false,
      hide_legend: false,
      hide_volume: false,
      hotlist: false,
      interval,
      locale,
      save_image: true,
      style: "1",
      symbol: tvSymbol,
      theme,
      timezone,
      backgroundColor: theme === "light" ? "#ffffff" : "#131722",
      gridColor: "rgba(46, 46, 46, 0.06)",
      watchlist: [],
      withdateranges: false,
      compareSymbols: [],
      studies: [],
      autosize: true,
    });

    containerRef.current.appendChild(script);
    scriptRef.current = script;

    return () => {
      if (
        scriptRef.current &&
        containerRef.current &&
        containerRef.current.contains(scriptRef.current)
      ) {
        containerRef.current.removeChild(scriptRef.current);
        scriptRef.current = null;
      }
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
    };
  }, [tvSymbol, interval, theme, locale, timezone]);

  return (
    <section aria-label="Trading chart" className="w-full" style={{ height: minHeight }}>
      <div ref={containerRef} className="h-full" />
      <div className="tradingview-widget-copyright">
        <a
          href={`https://www.tradingview.com/symbols/${String(tvSymbol).replace(":", "-")}/`}
          rel="noopener noreferrer nofollow"
          target="_blank"
          aria-label="Open symbol on TradingView"
        >
          <span className="blue-text">
            {String(tvSymbol).replace(":", "/")} chart
          </span>
        </a>
        <span className="trademark"> by TradingView</span>
      </div>
    </section>
  );
}

export default memo(TradingViewAdvancedChart);
