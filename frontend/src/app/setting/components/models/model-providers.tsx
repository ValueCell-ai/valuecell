import { Item, ItemGroup } from "@/components/ui/item";
import PngIcon from "@/components/valuecell/png-icon";
import ScrollContainer from "@/components/valuecell/scroll/scroll-container";
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
  return (
    <div className="flex flex-col gap-4 overflow-hidden *:px-6">
      <h2 className="font-semibold text-gray-950 text-lg">Model Provider</h2>

      <ScrollContainer>
        <ItemGroup>
          {providers.length === 0 ? (
            <div className="rounded-xl border border-gray-200 border-dashed px-4 py-6 text-center text-gray-400 text-sm">
              No providers available.
            </div>
          ) : (
            providers.map((provider) => {
              const isActive = provider.provider === selectedProvider;

              return (
                <Item
                  size="sm"
                  className={cn(
                    "cursor-pointer px-3 py-2.5",
                    isActive ? "bg-gray-100" : "bg-white hover:bg-gray-50",
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
                    <span>{provider.provider}</span>
                    <span className="font-normal text-gray-500 text-xs">
                      {provider.provider}
                    </span>
                  </div>
                </Item>
              );
            })
          )}
        </ItemGroup>
      </ScrollContainer>
    </div>
  );
}
