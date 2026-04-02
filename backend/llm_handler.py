"""LLM handler: wraps the Ollama REST API and provides a generate() method."""

import logging
from typing import Generator, Optional

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert research assistant specialised in analysing academic papers.

Your role:
- Answer questions based ONLY on the provided context excerpts from research papers.
- Cite specific information from the context when answering.
- If the context does not contain enough information to answer confidently, say so clearly.
- Keep answers concise, accurate, and well-structured.
- Use bullet points and headers where appropriate for clarity.
- Do NOT fabricate information that is not in the context.
"""


class LLMHandler:
    """Interface to the Ollama LLM service."""

    def __init__(
        self,
        base_url: str = settings.ollama_base_url,
        model: str = settings.ollama_model,
        temperature: float = settings.llm_temperature,
        max_tokens: int = settings.llm_max_tokens,
        timeout: int = settings.llm_timeout,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    # ── Public API ────────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Return *True* if the Ollama service responds within the configured timeout."""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        question: str,
        context_chunks: list[dict],
        temperature: Optional[float] = None,
    ) -> str:
        """Generate an answer for *question* given *context_chunks*.

        Falls back to a deterministic context-only response when the LLM is
        unavailable so the rest of the application keeps working.
        """
        if not self.is_available():
            logger.warning("Ollama unavailable – returning context-only answer")
            return self._fallback_answer(question, context_chunks)

        prompt = self._build_prompt(question, context_chunks)
        temp = temperature if temperature is not None else self.temperature

        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": SYSTEM_PROMPT,
                    "temperature": temp,
                    "num_predict": self.max_tokens,
                    "stream": False,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            answer = data.get("response", "").strip()
            if not answer:
                raise ValueError("Empty response from LLM")
            return answer
        except Exception as exc:
            logger.error("LLM generation failed: %s", exc)
            return self._fallback_answer(question, context_chunks)

    def generate_stream(
        self,
        question: str,
        context_chunks: list[dict],
        temperature: Optional[float] = None,
    ) -> Generator[str, None, None]:
        """Yield tokens as they stream from Ollama."""
        if not self.is_available():
            yield self._fallback_answer(question, context_chunks)
            return

        prompt = self._build_prompt(question, context_chunks)
        temp = temperature if temperature is not None else self.temperature

        try:
            import json as _json

            with httpx.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": SYSTEM_PROMPT,
                    "temperature": temp,
                    "num_predict": self.max_tokens,
                    "stream": True,
                },
                timeout=self.timeout,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        chunk = _json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            yield token
                        if chunk.get("done"):
                            break
        except Exception as exc:
            logger.error("LLM streaming failed: %s", exc)
            yield self._fallback_answer(question, context_chunks)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _build_prompt(question: str, context_chunks: list[dict]) -> str:
        """Assemble the RAG prompt from the question and retrieved chunks."""
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            filename = chunk.get("filename", "Unknown")
            content = chunk.get("content", "")
            score = chunk.get("relevance_score", 0.0)
            context_parts.append(
                f"[Source {i}: {filename} (relevance: {score:.2f})]\n{content}"
            )

        context_text = "\n\n---\n\n".join(context_parts)
        return (
            f"Context from research papers:\n\n{context_text}\n\n"
            f"---\n\nQuestion: {question}\n\nAnswer:"
        )

    @staticmethod
    def _fallback_answer(question: str, context_chunks: list[dict]) -> str:
        """Return a structured answer built directly from the retrieved context."""
        if not context_chunks:
            return (
                "I could not find any relevant information in the indexed documents "
                f'to answer your question: "{question}".\n\n'
                "Please make sure you have uploaded relevant research papers first."
            )

        lines = [
            f'Based on the retrieved context for: "{question}"\n',
            "Here are the most relevant excerpts:\n",
        ]
        for i, chunk in enumerate(context_chunks, 1):
            filename = chunk.get("filename", "Unknown")
            score = chunk.get("relevance_score", 0.0)
            content = chunk.get("content", "")[:400]
            lines.append(f"{i}. **{filename}** (relevance: {score:.2f})\n   {content}...\n")

        lines.append(
            "\n*Note: Full LLM analysis is unavailable. "
            "Please start Ollama (`ollama serve`) for AI-generated answers.*"
        )
        return "\n".join(lines)
