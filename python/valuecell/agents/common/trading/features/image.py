from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from agno.agent import Agent as AgnoAgent
from agno.models import Model as AgnoModel
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


class MLLMImageFeatureComputer(ImageBasedFeatureComputer):
    """Image feature computer using an MLLM (Gemini via agno Agent).

    Consumes dashboard screenshots and extracts structured trading insights,
    returning a single `FeatureVector` with textual features. Instrument is
    left unset (market-wide analysis).
    """

    def __init__(self, model: AgnoModel, prompt: str) -> None:
        """Initialize with a pre-built `Agent` instance.

        The agent's `.model` and `.model.id` are inspected for provider/model
        metadata.
        """
        self._model = model
        self._prompt = prompt
        self._agent = AgnoAgent(
            model=model,
            instructions=[self._prompt],
            markdown=True,
        )

    @classmethod
    def from_request(
        cls, request: UserRequest, prompt: str
    ) -> "MLLMImageFeatureComputer":
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

        return cls(created_model, prompt)

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
        # TODO: include image metadata such as filepath, url
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
