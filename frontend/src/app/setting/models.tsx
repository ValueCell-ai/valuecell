import { useEffect, useState } from "react";

import { useGetModelProviders } from "@/api/setting";
import { ModelDetail } from "./components/models/model-detail";
import { ModelProviders } from "./components/models/model-providers";

export default function ModelsSettingPage() {
  const { data: providers = [] } = useGetModelProviders();
  const [selectedProvider, setSelectedProvider] = useState<string>("");

  useEffect(() => {
    if (providers.length > 0) {
      setSelectedProvider(providers[0]?.provider || "");
    }
  }, [providers]);

  return (
    <div className="flex size-full overflow-hidden py-8">
      <ModelProviders
        providers={providers}
        selectedProvider={selectedProvider}
        onSelect={(provider) => setSelectedProvider(provider)}
      />

      {selectedProvider && <ModelDetail provider={selectedProvider} />}
    </div>
  );
}
