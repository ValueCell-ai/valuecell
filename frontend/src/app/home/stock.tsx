import { useMemo } from "react";
import { useParams } from "react-router";
import Sparkline from "@/components/valuecell/charts/sparkline";
import { stockData } from "@/mock/stock-data";

// 生成历史价格数据
function generateHistoricalData(basePrice: number, days: number = 30) {
  const data = [];
  const now = new Date();

  for (let i = days; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);

    // 模拟价格波动 (±5%)
    const variation = (Math.random() - 0.5) * 0.1;
    const price = basePrice * (1 + variation * (i / days)); // 添加趋势

    data.push({
      timestamp: date.toISOString(),
      value: Math.max(0, price),
    });
  }

  return data;
}

function Stock() {
  const { stockId } = useParams();

  // 从 mock 数据中查找股票信息
  const stockInfo = useMemo(() => {
    for (const group of stockData) {
      const stock = group.stocks.find((s) => s.symbol === stockId);
      if (stock) return stock;
    }
    return null;
  }, [stockId]);

  // 生成历史价格数据
  const chartData = useMemo(() => {
    if (!stockInfo) return [];
    return generateHistoricalData(stockInfo.price, 60); // 60天历史数据
  }, [stockInfo]);

  if (!stockInfo) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-gray-500 text-lg">未找到股票 {stockId}</div>
      </div>
    );
  }

  const isPositive = stockInfo.changePercent >= 0;
  const chartColor = isPositive ? "#41C3A9" : "#EF4444";
  const gradientColors: [string, string] = isPositive
    ? ["rgba(65, 195, 169, 0.6)", "rgba(65, 195, 169, 0)"]
    : ["rgba(239, 68, 68, 0.6)", "rgba(239, 68, 68, 0)"];

  return (
    <div className="space-y-6 p-6">
      {/* 股票信息头部 */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h1 className="font-bold text-2xl">{stockInfo.symbol}</h1>
          <div className="text-right">
            <div className="font-bold text-2xl">
              {stockInfo.currency}
              {stockInfo.price.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
            <div
              className={`font-medium text-sm ${
                isPositive ? "text-green-600" : "text-red-600"
              }`}
            >
              {isPositive ? "+" : ""}
              {stockInfo.changePercent.toFixed(2)}%
            </div>
          </div>
        </div>
        <div className="text-gray-600">{stockInfo.companyName}</div>
      </div>

      {/* 价格图表 */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="mb-4">
          <h2 className="font-semibold text-gray-900 text-lg">价格走势</h2>
          <p className="text-gray-500 text-sm">过去60天的价格变化</p>
        </div>

        <Sparkline
          data={chartData}
          color={chartColor}
          gradientColors={gradientColors}
          height={400}
          showGrid={true}
          showTooltip={true}
          formatTooltip={(value: number, timestamp: string) => {
            const date = new Date(timestamp);
            const formatDate = date.toLocaleDateString("zh-CN", {
              month: "short",
              day: "numeric",
            });
            const formatTime = date.toLocaleTimeString("zh-CN", {
              hour: "2-digit",
              minute: "2-digit",
            });

            return `
              <div style="font-weight: 500; font-size: 12px; margin-bottom: 8px; letter-spacing: -0.42px;">
                ${formatDate} ${formatTime}
              </div>
              <div style="font-weight: bold; font-size: 18px; font-family: 'SF Pro Display', sans-serif;">
                ${stockInfo.currency}${value.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            `;
          }}
        />
      </div>
    </div>
  );
}

export default Stock;
