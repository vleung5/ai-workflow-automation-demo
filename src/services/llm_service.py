"""LLM API calls - OpenAI/Claude integration"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LLMService:
    """
    Lightweight abstraction over LLM API providers.

    Extend this class to integrate OpenAI, Anthropic Claude, or any
    other LLM provider.  The current implementation uses a rule-based
    fallback so the service is functional without API keys.
    """

    def __init__(self, provider: str = "local", model: str = "rule-based"):
        self.provider = provider
        self.model = model
        logger.info(f"LLMService initialized (provider={provider}, model={model})")

    async def summarize(self, text: str, max_length: int = 150) -> str:
        """Generate a summary of the provided text"""
        if self.provider == "openai":
            return await self._openai_summarize(text, max_length)
        # Fallback: truncate first sentence
        first_sentence = text.split(".")[0].strip()
        return first_sentence[:max_length] if first_sentence else text[:max_length]

    async def classify(self, text: str, categories: list) -> Dict[str, Any]:
        """Classify text into one of the provided categories"""
        if self.provider == "openai":
            return await self._openai_classify(text, categories)
        # Fallback: return first category with low confidence
        return {
            "category": categories[0] if categories else "unknown",
            "confidence": 0.5,
        }

    async def _openai_summarize(self, text: str, max_length: int) -> str:
        """Call OpenAI API for summarization"""
        try:
            import openai  # type: ignore

            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"Summarize the following text in {max_length} characters or fewer."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
            )
            return response.choices[0].message.content.strip()
        except ImportError:
            logger.warning("openai package not installed; using fallback summarization")
            return text[:max_length]
        except Exception as e:
            logger.error(f"OpenAI summarization failed: {str(e)}")
            return text[:max_length]

    async def _openai_classify(self, text: str, categories: list) -> Dict[str, Any]:
        """Call OpenAI API for classification"""
        try:
            import openai  # type: ignore

            categories_str = ", ".join(categories)
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"Classify the following text into exactly one of: {categories_str}. "
                            "Respond with only the category name."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
            )
            category = response.choices[0].message.content.strip().lower()
            if category not in categories:
                category = categories[0]
            return {"category": category, "confidence": 0.9}
        except ImportError:
            logger.warning("openai package not installed; using fallback classification")
            return {
                "category": categories[0] if categories else "unknown",
                "confidence": 0.5,
            }
        except Exception as e:
            logger.error(f"OpenAI classification failed: {str(e)}")
            return {
                "category": categories[0] if categories else "unknown",
                "confidence": 0.5,
            }


# Module-level singleton
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
