import { Eye, Medal, Trophy } from "lucide-react";
import { useState } from "react";
import { useGetStrategyDetail, useGetStrategyList } from "@/api/system";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function RankBoard() {
  const [days, setDays] = useState(7);
  const [selectedStrategyId, setSelectedStrategyId] = useState<number | null>(
    null,
  );

  const { data: strategies, isLoading } = useGetStrategyList({
    limit: 10,
    days,
  });
  const { data: strategyDetail } = useGetStrategyDetail(selectedStrategyId);

  const getRankIcon = (rank: number) => {
    if (rank === 1) return <Trophy className="h-6 w-6 text-yellow-500" />;
    if (rank === 2) return <Medal className="h-6 w-6 text-gray-400" />;
    if (rank === 3) return <Medal className="h-6 w-6 text-amber-600" />;
    return <span className="font-bold text-gray-500 text-lg">{rank}</span>;
  };

  return (
    <div className="container mx-auto py-10">
      <Card className="border-none shadow-none">
        <CardHeader className="flex flex-row items-center justify-between px-0">
          <CardTitle className="font-bold text-xl">
            Profit Leaderboard
          </CardTitle>
          <Tabs
            value={String(days)}
            onValueChange={(val) => setDays(Number(val))}
          >
            <TabsList>
              <TabsTrigger value="1">1D</TabsTrigger>
              <TabsTrigger value="3">3D</TabsTrigger>
              <TabsTrigger value="7">1W</TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-[80px]">Rank</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Return</TableHead>
                <TableHead>Strategy</TableHead>
                <TableHead>Exchange</TableHead>
                <TableHead>Trading Portfolio</TableHead>
                <TableHead className="text-right">Details</TableHead>
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
                      <span className="font-bold text-green-500">
                        +{strategy.return_rate_pct.toFixed(2)}%
                      </span>
                    </TableCell>
                    <TableCell>{strategy.strategy_type}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {/* Placeholder for Exchange Icon */}
                        <div className="flex h-5 w-5 items-center justify-center rounded-full bg-gray-100 text-[10px]">
                          {strategy.exchange_id[0]}
                        </div>
                        {strategy.exchange_id}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="font-normal">
                          {strategy.llm_provider}/{strategy.llm_model_id}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedStrategyId(strategy.id)}
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
        </CardContent>
      </Card>

      <Dialog
        open={!!selectedStrategyId}
        onOpenChange={(open) => !open && setSelectedStrategyId(null)}
      >
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Strategy Details</DialogTitle>
          </DialogHeader>
          {strategyDetail ? (
            <div className="grid gap-4 py-4">
              <div className="flex items-center gap-4">
                <Avatar className="h-16 w-16">
                  <AvatarImage
                    src={strategyDetail.avatar}
                    alt={strategyDetail.name}
                  />
                  <AvatarFallback>{strategyDetail.name[0]}</AvatarFallback>
                </Avatar>
                <div>
                  <h3 className="font-bold text-lg">{strategyDetail.name}</h3>
                  <p className="text-gray-500 text-sm">
                    User ID: {strategyDetail.user_id}
                  </p>
                </div>
                <div className="ml-auto text-right">
                  <div className="font-bold text-2xl text-green-500">
                    +{strategyDetail.return_rate_pct.toFixed(2)}%
                  </div>
                  <div className="text-gray-500 text-sm">Return Rate</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <span className="font-medium text-gray-500 text-sm">
                    Strategy Type
                  </span>
                  <p>{strategyDetail.strategy_type}</p>
                </div>
                <div className="space-y-1">
                  <span className="font-medium text-gray-500 text-sm">
                    Exchange
                  </span>
                  <p>{strategyDetail.exchange}</p>
                </div>
                <div className="space-y-1">
                  <span className="font-medium text-gray-500 text-sm">
                    Initial Capital
                  </span>
                  <p>${strategyDetail.initial_capital}</p>
                </div>
                <div className="space-y-1">
                  <span className="font-medium text-gray-500 text-sm">
                    Max Leverage
                  </span>
                  <p>{strategyDetail.max_leverage}x</p>
                </div>
                <div className="col-span-2 space-y-1">
                  <span className="font-medium text-gray-500 text-sm">
                    Symbols
                  </span>
                  <div className="flex gap-2">
                    {strategyDetail.symbols.map((symbol) => (
                      <Badge key={symbol} variant="outline">
                        {symbol}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="col-span-2 space-y-1">
                  <span className="font-medium text-gray-500 text-sm">
                    Prompt
                  </span>
                  <p className="rounded-md bg-gray-50 p-3 text-gray-700 text-sm">
                    {strategyDetail.prompt}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="py-8 text-center">Loading details...</div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
