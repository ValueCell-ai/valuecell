import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useTauriInfo } from "@/hooks/use-tauri-info";
import { useUpdateToast } from "@/hooks/use-update-toast";
import type { StockColorMode } from "@/store/settings-store";
import { useSettingsActions, useStockColorMode } from "@/store/settings-store";

export default function GeneralPage() {
  const stockColorMode = useStockColorMode();
  const { setStockColorMode } = useSettingsActions();
  const { checkAndUpdate } = useUpdateToast();
  const { isTauriApp, appVersion } = useTauriInfo();

  return (
    <div className="flex flex-col gap-5 px-16 py-10">
      <div className="flex flex-col gap-1.5">
        <h1 className="font-bold text-gray-950 text-xl">General</h1>
        <p className="text-base text-gray-400 leading-[22px]">
          Manage your preferences and application settings
        </p>
      </div>

      <div className="space-y-6">
        <div className="space-y-4">
          <h3 className="font-medium text-foreground text-sm">Quotes Color</h3>

          <RadioGroup
            value={stockColorMode}
            onValueChange={(value) =>
              setStockColorMode(value as StockColorMode)
            }
          >
            <Label
              htmlFor="green-up"
              className="flex cursor-pointer items-center space-x-3 rounded-lg border border-input p-4 hover:bg-accent/50"
            >
              <RadioGroupItem value="GREEN_UP_RED_DOWN" id="green-up" />
              <span className="flex-1">Green Up / Red Down</span>
            </Label>

            <Label
              htmlFor="red-up"
              className="flex cursor-pointer items-center space-x-3 rounded-lg border border-input p-4 hover:bg-accent/50"
            >
              <RadioGroupItem value="RED_UP_GREEN_DOWN" id="red-up" />
              <span className="flex-1">Red Up / Green Down</span>
            </Label>
          </RadioGroup>
        </div>

        {isTauriApp && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-medium text-foreground text-sm">
                App Updates
              </h3>
              <Badge variant="secondary">
                {appVersion ? `v${appVersion}` : "—"}
              </Badge>
            </div>

            <Button size="sm" onClick={checkAndUpdate}>
              Check for Updates
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
