import { MarkdownRenderer } from "@/components/valuecell/renderer";

export default function Test() {
  return (
    <div className="scroll-container">
      <MarkdownRenderer
        content="| Symbol | Type | **Position/Quantity** | **Current/Avg** | P&L |
| :--- | :--- | :---: | :---: | :---: |
| BTC-USD | LONG | 0.0180 <br/> **$2,001.31** | $111,265.29<br>**$111,338.45** | 🟢 +$1.31 |
| ETH-USD | LONG | 0.4982 <br/> **$1,962.49** | $3,934.43<br>**$3,939.42** | 🟢 +$2.49 |
| BTC-USD | LONG | 0.0180 <br/> **$2,001.31** | $111,265.29<br>**$111,338.45** | 🟢 +$1.31 |
| ETH-USD | LONG | 0.4982 <br/> **$1,962.49** | $3,934.43<br>**$3,939.42** | 🟢 +$2.49 |
| BTC-USD | LONG | 0.0180 <br/> **$2,001.31** | $111,265.29<br>**$111,338.45** | 🟢 +$1.31 |
| ETH-USD | LONG | 0.4982 <br/> **$1,962.49** | $3,934.43<br>**$3,939.42** | 🟢 +$2.49 |
| BTC-USD | LONG | 0.0180 <br/> **$2,001.31** | $111,265.29<br>**$111,338.45** | 🟢 +$1.31 |
| ETH-USD | LONG | 0.4982 <br/> **$1,962.49** | $3,934.43<br>**$3,939.42** | 🟢 +$2.49 |"
      />
    </div>
  );
}
