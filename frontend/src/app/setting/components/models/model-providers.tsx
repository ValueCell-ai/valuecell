import { useTranslation } from "react-i18next";
import { Item, ItemGroup } from "@/components/ui/item";
import PngIcon from "@/components/valuecell/icon/png-icon";
import { MODEL_PROVIDER_ICONS } from "@/constants/icons";
import { cn } from "@/lib/utils";
import type { ModelProvider } from "@/types/setting";

type ModelProvidersProps = {
  providers: ModelProvider[];
  selectedProvider?: string;
  onSelect: (provider: string) => void;
};

export function ModelProviders({
  providers,
  selectedProvider,
  onSelect,
}: ModelProvidersProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-4 overflow-hidden *:px-6">
      <h2 className="font-semibold text-foreground text-lg">
        {t("settings.models.title")}
      </h2>

      <ItemGroup className="scroll-container">
        {providers.length === 0 ? (
          <div className="rounded-xl border border-border border-dashed px-4 py-6 text-center text-muted-foreground text-sm">
            {t("settings.models.noProviders")}
          </div>
        ) : (
          providers.map((provider) => {
            const isActive = provider.provider === selectedProvider;

            return (
              <Item
                size="sm"
                className={cn(
                  "cursor-pointer px-3 py-2.5",
                  isActive ? "bg-muted" : "bg-card hover:bg-muted",
                )}
                key={provider.provider}
                onClick={() => onSelect(provider.provider)}
              >
                <PngIcon
                  src={
                    MODEL_PROVIDER_ICONS[
                      provider.provider as keyof typeof MODEL_PROVIDER_ICONS
                    ]
                  }
                  className="size-6"
                />
                <div className="flex flex-1 flex-col text-left">
                  <span>
                    {t(`strategy.providers.${provider.provider}`) ||
                      provider.provider}
                  </span>
                  <span className="font-normal text-muted-foreground text-xs">
                    {provider.provider}
                  </span>
                </div>
              </Item>
            );
          })
        )}
      </ItemGroup>
    </div>
  );
}
