## run project

```bash
bun dev
```

## for development
### temporarily test agent
1. change `agentData` in `src/mock/agent-data.tsx`
2. add agent info in `agentData`
   ```tsx
   "WarrenBuffettAgent" :{
    name: "WarrenBuffettAgent",
    description: "Looking for high-quality companies at fair prices, with a focus on moats and long-term value.",
    avatar: (
      <div className="relative size-12">
        <div className="absolute inset-0 rounded-full bg-[#D9D9D9]" />
        <div className="absolute inset-0 rounded-full bg-gradient-to-br from-gray-300 to-gray-400" />
      </div>
    ),
    content: `## Introduction

    This AI Agent is not a simple stock selection tool or market predictor, but a decision assistance system that deeply integrates Warren Buffett's core investment philosophy with modern artificial intelligence technology. Its mission is to help users think like Buffett and systematically identify and hold high-quality companies in the global capital market for the long term.
    `,
   },
   ```
3. visit `http://localhost:1420/agent/WarrenBuffettAgent`
