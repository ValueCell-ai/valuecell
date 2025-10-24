import { type MemoryItem, MemoryItemCard } from "./components";

// Mock data - replace with API call later
const mockMemories: MemoryItem[] = [
  {
    id: "1",
    content:
      'Users hope to receive the latest Chinese news updates about Tesla every morning at 9am (Beijing time), in the format of "Date | Title | Abstract | Source Link", with a total of 5 articles',
  },
  {
    id: "2",
    content:
      "Users hope to receive the latest Chinese news updates about Tesla every morning at 9am (Beijing time), in the forma",
  },
  {
    id: "3",
    content:
      "Users hope to receive the latest Chinese news updates about Tesla every morning at 9am (Beijing time), in the forma",
  },
];

export default function MemoryPage() {
  const handleDelete = (id: string) => {
    // TODO: Implement delete functionality with API call
    console.log("Delete memory:", id);
  };

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
        {mockMemories.map((memory) => (
          <MemoryItemCard
            key={memory.id}
            item={memory}
            onDelete={handleDelete}
          />
        ))}
      </div>
    </div>
  );
}
