import { ChevronDown, History } from "lucide-react";
import { type FC, memo, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { ValueCellAgentPng } from "@/assets/png";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { PngIcon } from "@/components/valuecell/icon/png-icon";
import { TIME_FORMATS, TimeUtils } from "@/lib/time";
import {
  formatChange,
  getChangeType,
  getCoinCapIcon,
  isNullOrUndefined,
  numberFixed,
} from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";
import type {
  Strategy,
  StrategyAction,
  StrategyCompose,
} from "@/types/strategy";

interface StrategyComposeItemProps {
  compose: StrategyCompose;
}

const StrategyComposeItem: FC<StrategyComposeItemProps> = ({ compose }) => {
  const { t } = useTranslation();
  const [isReasoningOpen, setIsReasoningOpen] = useState(false);

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-muted p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-base text-foreground">
          {t("strategy.history.cycle", { index: compose.cycle_index })}
        </h3>
        <span className="text-muted-foreground text-xs">
          {TimeUtils.formatUTC(compose.created_at, TIME_FORMATS.DATETIME)}
        </span>
      </div>

      {/* AI Reasoning Logic */}
      <p className="text-muted-foreground text-xs">
        {t("strategy.history.aiReasoning")}
      </p>
      <Collapsible open={isReasoningOpen} onOpenChange={setIsReasoningOpen}>
        <CollapsibleTrigger
          data-active={isReasoningOpen}
          className="flex w-full cursor-pointer items-start justify-between rounded-md border-gradient bg-card px-3 py-2 text-left"
        >
          <span
            className={`text-foreground text-sm leading-relaxed ${
              isReasoningOpen ? "" : "line-clamp-1"
            }`}
          >
            {compose.rationale}
          </span>
          <ChevronDown
            className={`mt-1 ml-2 size-4 shrink-0 text-muted-foreground transition-transform duration-200 ${
              isReasoningOpen ? "rotate-180" : ""
            }`}
          />
        </CollapsibleTrigger>
      </Collapsible>

      {/* Perform Operation */}
      {compose.actions.length > 0 && (
        <>
          <p className="text-muted-foreground text-xs">
            {t("strategy.history.operation")}
          </p>
          {compose.actions.map((action) => (
            <ActionItem key={action.instruction_id} action={action} />
          ))}
        </>
      )}
    </div>
  );
};

const ActionItem: FC<{ action: StrategyAction }> = ({ action }) => {
  const { t } = useTranslation();
  const stockColors = useStockColors();

  const formatHoldingTime = (ms?: number) => {
    if (isNullOrUndefined(ms)) return "-";
    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}H ${minutes}M`;
  };

  const priceRange = action.exit_price
    ? `${numberFixed(action.entry_price, 4)} → ${numberFixed(action.exit_price, 4)}`
    : `${numberFixed(action.entry_price, 4)}`;

  const [pnl_value, changeType] = useMemo(() => {
    if (!action.action.includes("close"))
      return ["-", getChangeType(undefined)];

    const changeType = getChangeType(action.realized_pnl);
    const formatPnl = formatChange(action.realized_pnl, "", 4);
    return [formatPnl, changeType];
  }, [action.realized_pnl, action.action]);

  return (
    <HoverCard openDelay={300}>
      <HoverCardTrigger asChild>
        <Button className="flex items-center justify-between rounded-md border-gradient bg-card p-3">
          <div className="flex items-center gap-2">
            <PngIcon
              src={getCoinCapIcon(action.symbol)}
              className="size-5"
              callback={ValueCellAgentPng}
            />
            <span className="font-medium text-foreground text-sm">
              {action.symbol}
            </span>

            <Badge variant="outline">{action.action_display}</Badge>
            <Badge variant="outline">{action.leverage}X</Badge>
          </div>

          {action.realized_pnl !== 0 && (
            <span
              className="font-medium text-sm"
              style={{ color: stockColors[changeType] }}
            >
              {pnl_value}
            </span>
          )}
        </Button>
      </HoverCardTrigger>
      <HoverCardContent
        className="rounded-xl border border-border p-4 shadow-[0_-4px_100px_8px_rgba(17,17,17,0.08)]"
        side="right"
      >
        {/* HoverCard Header */}
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PngIcon
              src={getCoinCapIcon(action.symbol)}
              className="size-5"
              callback={ValueCellAgentPng}
            />
            <span className="font-bold text-base text-foreground">
              {action.symbol}
            </span>
          </div>

          <span
            className="font-medium"
            style={{ color: stockColors[changeType] }}
          >
            {pnl_value}
          </span>
        </div>

        {/* Popover Tags */}
        <div className="mb-4 flex gap-2">
          <span className="rounded-md bg-muted px-2 py-1 font-medium text-foreground text-xs">
            {action.action_display}
          </span>
          <span className="rounded-md bg-muted px-2 py-1 font-medium text-foreground text-xs">
            {action.leverage}X
          </span>
        </div>

        {/* Data Grid */}
        <div className="mb-4 grid grid-cols-[auto_1fr] gap-y-1 text-nowrap text-muted-foreground text-xs">
          <span>{t("strategy.history.details.time")}</span>
          <span className="text-right">
            {TimeUtils.formatUTC(
              action.exit_at ?? action.entry_at,
              TIME_FORMATS.DATETIME,
            )}
          </span>

          <span>{t("strategy.history.details.price")}</span>
          <span className="text-right">{priceRange}</span>

          <span>{t("strategy.history.details.quantity")}</span>
          <span className="text-right">{action.quantity}</span>

          <span>{t("strategy.history.details.holdingTime")}</span>
          <span className="text-right">
            {formatHoldingTime(action.holding_time_ms)}
          </span>

          <span>{t("strategy.history.details.tradingFee")}</span>
          <span className="text-right">{-numberFixed(action.fee_cost, 4)}</span>
        </div>

        {/* Reasoning Box */}
        <div className="rounded-lg bg-muted p-3">
          <p className="mb-1 font-medium text-foreground text-xs">
            {t("strategy.history.details.reasoning")}
          </p>
          <p className="text-muted-foreground text-xs leading-relaxed">
            {action.rationale}
          </p>
        </div>
      </HoverCardContent>
    </HoverCard>
  );
};

interface StrategyComposeListProps {
  composes: StrategyCompose[];
  tradingMode: Strategy["trading_mode"];
}

const StrategyComposeList: FC<StrategyComposeListProps> = ({
  composes,
  tradingMode,
}) => {
  const { t } = useTranslation();
  return (
    <div className="flex w-[420px] flex-col overflow-hidden border-border border-r bg-card">
      <div className="flex items-center justify-between px-6 py-4">
        <h3 className="font-semibold text-base text-foreground">
          {t("strategy.history.title")}
        </h3>

        <p className="rounded-md bg-muted px-2.5 py-1 font-medium text-foreground text-sm">
          {tradingMode === "live"
            ? t("strategy.history.live")
            : t("strategy.history.virtual")}
        </p>
      </div>

      <div className="scroll-container flex-1 px-6">
        {composes.length > 0 ? (
          <div className="flex flex-col gap-4">
            {composes.map((compose) => (
              <StrategyComposeItem key={compose.compose_id} compose={compose} />
            ))}
          </div>
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <div className="flex flex-col items-center gap-4 px-6 py-12 text-center">
              <div className="flex size-14 items-center justify-center rounded-full bg-muted">
                <History className="size-7 text-muted-foreground" />
              </div>
              <div className="flex flex-col gap-2">
                <p className="font-semibold text-base text-foreground">
                  {t("strategy.history.empty.title")}
                </p>
                <p className="max-w-[280px] text-muted-foreground text-sm leading-relaxed">
                  {t("strategy.history.empty.desc")}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default memo(StrategyComposeList);
