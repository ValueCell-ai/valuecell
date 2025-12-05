import { useEffect, useMemo, useRef } from "react";

type Props = {
  symbols: readonly string[];
  theme?: "light" | "dark";
  locale?: string;
};

function TradingViewTickerTape({
  symbols,
  theme = "light",
  locale = "en",
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const scriptRef = useRef<HTMLScriptElement | null>(null);

  const tapeSymbols = useMemo(
    () => symbols.slice(0, 8).map((s) => ({ proName: s })),
    [symbols],
  );

  useEffect(() => {
    if (!containerRef.current) return;

    if (scriptRef.current && containerRef.current.contains(scriptRef.current)) {
      containerRef.current.removeChild(scriptRef.current);
      scriptRef.current = null;
    }

    containerRef.current.innerHTML = "";

    const script = document.createElement("script");
    script.type = "text/javascript";
    script.async = true;
    script.src =
      "https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js";
    script.innerHTML = JSON.stringify({
      symbols: tapeSymbols,
      showSymbolLogo: true,
      colorTheme: theme,
      isTransparent: false,
      displayMode: "regular",
      locale,
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
  }, [tapeSymbols, theme, locale]);

  return (
    <div className="w-full">
      <div ref={containerRef} />
    </div>
  );
}

export default TradingViewTickerTape;
