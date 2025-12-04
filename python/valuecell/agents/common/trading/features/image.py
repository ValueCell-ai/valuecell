from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from agno.agent import Agent
from agno.media import Image as AgnoImage
from loguru import logger

from valuecell.utils import model as model_utils
from valuecell.utils.ts import get_current_timestamp_ms

from ..constants import (
    FEATURE_GROUP_BY_IMAGE_ANALYSIS,
    FEATURE_GROUP_BY_KEY,
)
from ..models import (
    FeatureVector,
    UserRequest,
)
from .interfaces import (
    ImageBasedFeatureComputer,
)

if TYPE_CHECKING:
    from valuecell.agents.common.trading.models import DataSourceImage


PROMPTS: str = """
# Role
You are an expert High-Frequency Trader (HFT) and Order Flow Analyst specializing in crypto market microstructure. You are analyzing a dashboard from Aggr.trade.

# Visual Context
The image displays three vertical panes:
1.  **Top (Price & Global CVD):** 5s candles, Aggregate Volume, Liquidations (bright bars), and Global CVD line.
2.  **Middle (Delta Grid):** Net Delta per exchange/pair (5m timeframe). Key: Spot (S) vs. Perps (P).
3.  **Bottom (Exchange CVDs):** Cumulative Volume Delta lines for individual exchanges (15m timeframe). 
	*   *Legend Assumption:* Cyan/Blue = Coinbase (Spot); Yellow/Red = Binance (Spot/Perps).

# Analysis Objectives
Please analyze the order flow dynamics and provide a scalping strategy based on the following:

1.  **Spot vs. Perp Dynamics:** 
	*   Is the price action driven by Spot demand (e.g., Coinbase buying) or Perp speculation?
	*   Identify any **"Spot Premium"** or **"Perp Discount"** behavior.

2.  **Absorption & Divergences (CRITICAL):**
	*   Look for **"Passive Absorption"**: Are we seeing aggressive selling (Red Delta/CVD) resulting in stable or rising prices?
	*   Look for **"CVD Divergences"**: Is Price making Higher Highs while Global/Binance CVD makes Lower Highs?

3.  **Exchange Specific Flows:**
	*   Compare **Coinbase Spot (Smart Money)** vs. **Binance Perps (Retail/Speculative)**. Are they correlated or fighting each other?

# Output Format
Provide a concise professional report:
*   **Market State:** (e.g., Spot-Led Grind, Short Squeeze, Liquidation Cascade)
*   **Key Observation:** (One sentence on the most critical anomaly, e.g., "Coinbase bidding while Binance dumps.")
*   **Trade Setup:** 
	*   **Bias:** [LONG / SHORT / NEUTRAL]
	*   **Entry Trigger:** (e.g., "Enter on retest of VWAP with absorption.")
	*   **Invalidation:** (Where does the thesis fail?)
"""


class MLLMImageFeatureComputer(ImageBasedFeatureComputer):
    """Image feature computer using an MLLM (Gemini via agno Agent).

    Consumes dashboard screenshots and extracts structured trading insights,
    returning a single `FeatureVector` with textual features. Instrument is
    left unset (market-wide analysis).
    """

    def __init__(self, agent: Agent):
        """Initialize with a pre-built `Agent` instance.

        The agent's `.model` and `.model.id` are inspected for provider/model
        metadata.
        """
        self._agent = agent
        self._model = agent.model

    @classmethod
    def from_request(cls, request: UserRequest) -> "MLLMImageFeatureComputer":
        """Create an instance from an `LLMModelConfig`.

        Builds a model via `model_utils.create_model_with_provider` and
        constructs an `Agent` that will be reused for image analysis.
        """
        llm_cfg = request.llm_model_config
        created_model = model_utils.create_model_with_provider(
            provider=llm_cfg.provider,
            model_id=llm_cfg.model_id,
            api_key=llm_cfg.api_key,
        )

        # Validate that the model declares image support in config
        if not model_utils.supports_model_images(llm_cfg.provider, llm_cfg.model_id):
            raise RuntimeError(
                f"Model {llm_cfg.model_id} from provider {llm_cfg.provider} does not declare support for images"
            )

        agent = Agent(
            model=created_model,
            markdown=True,
            instructions=[PROMPTS],
        )

        return cls(agent=agent)

    async def compute_features(
        self,
        images: Optional[List["DataSourceImage"]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> List[FeatureVector]:
        if not images:
            logger.warning("No images provided for image feature computation")
            return []

        logger.info("Running MLLM analysis on provided images: {}", images)
        # Convert DataSourceImage -> agno.media.Image for the agent
        agno_images: List[AgnoImage] = []
        for ds in images:
            try:
                if content := ds.content:
                    agno_images.append(AgnoImage(content=content))
                    continue

                if filepath := ds.filepath:
                    agno_images.append(AgnoImage(filepath=filepath))
                    continue

                if url := ds.url:
                    agno_images.append(AgnoImage(url=url))

            except Exception as e:
                logger.warning("Failed to convert DataSourceImage to agno.Image: {}", e)

        resp = await self._agent.arun(
            "analyze the trading dashboard configuration in the provided image and generate a brief report.",
            images=agno_images,
        )

        content: str = getattr(resp, "content", "") or ""
        logger.info("MLLM analysis complete: {}", content)

        # Store only the raw markdown report as requested.
        values: Dict[str, Any] = {"report_markdown": content}
        meta = meta or {}
        fv_meta = {
            FEATURE_GROUP_BY_KEY: FEATURE_GROUP_BY_IMAGE_ANALYSIS,
            **meta,
        }
        instrument = images[0].instrument
        fv = FeatureVector(
            ts=get_current_timestamp_ms(),
            instrument=instrument,
            values=values,
            meta=fv_meta,
        )
        return [fv]
