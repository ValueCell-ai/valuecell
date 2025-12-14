import { useTranslation } from "react-i18next";
import { useGetMemoryList, useRemoveMemory } from "@/api/setting";
import { MemoryItemCard } from "./components/memory";

export default function MemoryPage() {
  const { t } = useTranslation();
  const { data: memories = [], isLoading } = useGetMemoryList();
  const { mutate: removeMemory } = useRemoveMemory();

  const handleDelete = (id: number) => {
    removeMemory(id);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col gap-5 px-16 py-10">
        <div className="flex flex-col gap-1.5">
          <h1 className="font-bold text-gray-950 text-xl">
            {t("settings.memory.title")}
          </h1>
          <p className="text-base text-gray-400 leading-[22px]">
            {t("settings.memory.description")}
          </p>
        </div>
        <div className="flex items-center justify-center py-12 text-gray-400">
          {t("settings.memory.loading")}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5 px-16 py-10">
      {/* Title section */}
      <div className="flex flex-col gap-1.5">
        <h1 className="font-bold text-gray-950 text-xl">{t("settings.memory.title")}</h1>
        <p className="text-base text-gray-400 leading-[22px]">
          {t("settings.memory.description")}
        </p>
      </div>

      {/* Memory list */}
      <div className="flex flex-1 flex-col gap-4 overflow-y-auto">
        {memories.length === 0 ? (
          <div className="flex items-center justify-center py-12 text-gray-400">
            {t("settings.memory.noMemories")}
          </div>
        ) : (
          memories.map((memory) => (
            <MemoryItemCard
              key={memory.id}
              item={memory}
              onDelete={handleDelete}
            />
          ))
        )}
      </div>
    </div>
  );
}
