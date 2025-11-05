// Strategy types

export interface Strategy {
  strategyId: string;
  name: string;
  status: "running" | "stopped";
  tradingMode: "live" | "virtual";
  unrealized_pnl: number;
}
