import { Eye } from "lucide-react";
import { useRef, useState } from "react";
import { useGetStrategyList } from "@/api/system";
import { ValueCellAgentPng } from "@/assets/png";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tag } from "@/components/valuecell/button/tag-groups";
import { Rank1Icon, Rank2Icon, Rank3Icon } from "@/components/valuecell/icon";
import { PngIcon } from "@/components/valuecell/icon/png-icon";
import { EXCHANGE_ICONS } from "@/constants/icons";
import { getChangeType, numberFixed } from "@/lib/utils";
import { useStockColors } from "@/store/settings-store";
import StrategyRemoteModal, {
  type StrategyRemoteModalRef,
} from "./components/strategy-remote-modal";

export default function RankBoard() {
  const [days, setDays] = useState(7);
  const strategyRemoteModalRef = useRef<StrategyRemoteModalRef>(null);

  const stockColors = useStockColors();

  const { data: strategies, isLoading } = useGetStrategyList({
    limit: 30,
    days,
  });

  const getRankIcon = (rank: number) => {
    if (rank === 1) return <Rank1Icon />;
    if (rank === 2) return <Rank2Icon />;
    if (rank === 3) return <Rank3Icon />;
    return <span className="text-gray-950 text-sm">{rank}</span>;
  };

  const handleViewStrategy = (strategyId: number) => {
    strategyRemoteModalRef.current?.open(strategyId);
  };

  return (
    <div className="flex size-full flex-col p-6">
      <Card className="border-none p-0 shadow-none">
        <CardHeader className="flex flex-row items-center justify-between px-0">
          <CardTitle className="font-bold text-xl">
            Profit Leaderboard
          </CardTitle>
          <Tabs
            value={String(days)}
            onValueChange={(val) => setDays(Number(val))}
          >
            <TabsList>
              <TabsTrigger value="7">7D</TabsTrigger>
              <TabsTrigger value="30">1M</TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent className="px-0">
          <div className="scroll-container max-h-[82vh]">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-[80px]">Rank</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>P&L</TableHead>
                  <TableHead>Strategy</TableHead>
                  <TableHead>Exchange</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="h-24 text-center">
                      Loading...
                    </TableCell>
                  </TableRow>
                ) : (
                  strategies?.map((strategy, index) => (
                    <TableRow key={strategy.id} className="hover:bg-gray-50/50">
                      <TableCell className="font-medium">
                        <div className="flex w-8 items-center justify-center">
                          {getRankIcon(index + 1)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <Avatar className="h-8 w-8">
                            <AvatarImage
                              src={strategy.avatar}
                              alt={strategy.name}
                            />
                            <AvatarFallback>{strategy.name[0]}</AvatarFallback>
                          </Avatar>
                          <span className="font-medium">{strategy.name}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span
                          className="font-bold"
                          style={{
                            color:
                              stockColors[
                                getChangeType(strategy.return_rate_pct)
                              ],
                          }}
                        >
                          {numberFixed(strategy.return_rate_pct, 2)}%
                        </span>
                      </TableCell>
                      <TableCell>{strategy.strategy_type}</TableCell>
                      <TableCell>
                        <Tag>
                          <PngIcon
                            src={
                              EXCHANGE_ICONS[
                                strategy.exchange_id as keyof typeof EXCHANGE_ICONS
                              ]
                            }
                            className="size-4"
                            callback={ValueCellAgentPng}
                          />
                          {strategy.exchange_id}
                        </Tag>
                      </TableCell>
                      <TableCell>
                        <Tag>{strategy.llm_model_id}</Tag>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleViewStrategy(strategy.id)}
                          className="gap-2"
                        >
                          <Eye className="h-4 w-4" />
                          View
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <StrategyRemoteModal ref={strategyRemoteModalRef} />
    </div>
  );
}
