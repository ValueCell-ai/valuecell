import { useGetMemoryList, useRemoveMemory } from "@/api/setting";
import { MemoryItemCard } from "./components/memory";

export default function MemoryPage() {
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
            Preserved memories
          </h1>
          <p className="text-base text-gray-400 leading-[22px]">
            I will remember and automatically manage useful information in chats
            to enhance the personalization and relevance of replies
          </p>
        </div>
        <div className="flex items-center justify-center py-12 text-gray-400">
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5 px-16 py-10">
      {/* Title section */}
      <div className="flex flex-col gap-1.5">
        <h1 className="font-bold text-gray-950 text-xl">Preserved memories</h1>
        <p className="text-base text-gray-400 leading-[22px]">
          I will remember and automatically manage useful information in chats
          to enhance the personalization and relevance of replies
        </p>
      </div>

      {/* Memory list */}
      <div className="flex flex-1 flex-col gap-4 overflow-y-auto">
        {memories.length === 0 ? (
          <div className="flex items-center justify-center py-12 text-gray-400">
            No memories yet
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
