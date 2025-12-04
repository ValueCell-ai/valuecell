from pydantic import BaseModel, Field


class TradingViewConfig(BaseModel):
    symbol: str
    allow_symbol_change: bool = False
    calendar: bool = False
    details: bool = False
    hide_side_toolbar: bool = True
    hide_top_toolbar: bool = True
    hide_legend: bool = False
    hide_volume: bool = False
    hotlist: bool = False
    interval: str = "D"
    locale: str = "en"
    save_image: bool = False
    style: str = "1"
    theme: str = "light"
    timezone: str = "Etc/UTC"
    backgroundColor: str = "#ffffff"
    gridColor: str = "rgba(46, 46, 46, 0.06)"
    watchlist: list[str] = Field(default_factory=list)
    withdateranges: bool = False
    compareSymbols: list[str] = Field(default_factory=list)
    studies: list[str] = Field(default_factory=list)
    autosize: bool = True


def generate_tradingview_html(symbol: str) -> str:
    widget_config = TradingViewConfig(symbol=symbol)
    config_json = widget_config.model_dump_json(indent=2)
    html_content = f"""
<html><body style='margin:0;height:100vh;width:100vw'>
<!-- TradingView Widget BEGIN -->
<div class="tradingview-widget-container" style="height:100%;width:100%">
  <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
  <div class="tradingview-widget-copyright"><span class="trademark"> by TradingView</span></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
  {config_json}
  </script>
</div>
<!-- TradingView Widget END -->
</body></html>
"""
    return html_content
