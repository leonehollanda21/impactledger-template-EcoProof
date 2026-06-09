"""
app/services/vision_service.py
────────────────────────────────
Validação de imagens de limpeza usando Google Gemini AI.

Substitui o Google Cloud Vision anterior.
Diferenciais:
  - Entende contexto real (não só labels isolados)
  - Analisa as 2 fotos juntas em uma única requisição
  - Responde em JSON estruturado com approved, score e motivo em pt-BR
  - Setup: apenas GEMINI_API_KEY no .env (sem service account)

Fallback automático:
  - Se GEMINI_API_KEY não estiver configurada → approved=True, score=0.85
    (modo dev, sem bloquear o fluxo)

Limite gratuito (gemini-1.5-flash):
  - 15 req/min | 1.500 req/dia | 1M tokens/dia
"""
import json
import logging
import re
from dataclasses import dataclass
from io import BytesIO

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# Limite em bytes para download das imagens antes de enviar ao Gemini
_MAX_IMAGE_BYTES = 4 * 1024 * 1024  # 4 MB


@dataclass
class VisionResult:
    approved: bool
    score: float
    motivo: str


# ── Prompt de análise ─────────────────────────────────────────────────────────

_PROMPT = """\
Você é um validador de ações ambientais da plataforma EcoProof.
Receberá duas fotos de um mesmo local: a primeira ANTES da limpeza e a segunda DEPOIS.

Sua tarefa:
1. Verificar se a foto ANTES mostra claramente sujeira, lixo, entulho ou poluição.
2. Verificar se a foto DEPOIS mostra melhora real e significativa em relação à foto ANTES.
3. Atribuir um score de 0.0 a 1.0 para a melhoria (0 = nenhuma melhoria, 1 = totalmente limpo).
4. Decidir se a ação deve ser APROVADA (score >= 0.5 e presença de sujeira verificada no ANTES).

Responda SOMENTE com um JSON válido, sem markdown, sem explicação extra:
{
  "approved": true,
  "score": 0.85,
  "motivo": "Explique em 1-2 frases em português o que foi observado."
}
"""


# ── Download de imagem ────────────────────────────────────────────────────────

async def _download_image(url: str) -> tuple[bytes, str]:
    """
    Baixa uma imagem de URL pública e retorna (bytes, mime_type).
    Lança HTTPException 502 se o download falhar.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            content = resp.content
            mime = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
            return content[:_MAX_IMAGE_BYTES], mime
    except httpx.HTTPStatusError as exc:
        logger.error("Falha ao baixar imagem %s: %s", url, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Não foi possível acessar a imagem de análise: {url}",
        )
    except Exception as exc:
        logger.error("Erro no download de imagem: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao baixar imagem para análise.",
        )


# ── Fallback simulado ─────────────────────────────────────────────────────────

def _simulate_analysis() -> VisionResult:
    """
    Retorna resultado simulado quando GEMINI_API_KEY não está configurada.
    Ideal para desenvolvimento local sem gastar quota.
    """
    logger.warning(
        "MODO SIMULADO: GEMINI_API_KEY não configurada. "
        "Aprovando limpeza automaticamente para desenvolvimento."
    )
    return VisionResult(
        approved=True,
        score=0.85,
        motivo=(
            "[SIMULADO] Gemini AI não configurado. "
            "Limpeza aprovada automaticamente para fins de desenvolvimento."
        ),
    )


# ── Parser da resposta Gemini ─────────────────────────────────────────────────

def _parse_gemini_response(text: str) -> VisionResult:
    """
    Extrai e valida o JSON retornado pelo Gemini.
    Tolerante a markdown residual (```json ... ```).
    """
    # Remove blocos de código markdown caso existam
    clean = re.sub(r"```(?:json)?|```", "", text).strip()

    try:
        data = json.loads(clean)
        approved = bool(data.get("approved", False))
        score = float(data.get("score", 0.0))
        score = max(0.0, min(1.0, score))  # garante [0, 1]
        motivo = str(data.get("motivo", "Análise concluída."))
        return VisionResult(approved=approved, score=round(score, 4), motivo=motivo)
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        logger.warning("Resposta Gemini não parseável: %r — erro: %s", text, exc)
        # Fallback conservador: não aprova mas não quebra
        return VisionResult(
            approved=False,
            score=0.0,
            motivo=(
                "Análise automática inconclusiva. "
                "A limpeza será revisada manualmente por um administrador."
            ),
        )


# ── Função principal ──────────────────────────────────────────────────────────

async def analyze_cleanup(url_antes: str, url_depois: str) -> VisionResult:
    """
    Analisa o par de fotos (antes/depois) de uma limpeza com Gemini AI.

    Args:
        url_antes: URL pública da foto do local ANTES da limpeza.
        url_depois: URL pública da foto do local DEPOIS da limpeza.

    Returns:
        VisionResult com approved, score (0.0–1.0) e motivo em pt-BR.

    Raises:
        502: Falha ao baixar imagens ou comunicação com Gemini.
    """
    # Modo simulado quando não há API key
    if not settings.GEMINI_API_KEY:
        return _simulate_analysis()

    try:
        import google.generativeai as genai  # type: ignore[import]
        from google.generativeai import types as genai_types  # type: ignore[import]
    except ImportError:
        logger.warning("google-generativeai não instalado. Usando modo simulado.")
        return _simulate_analysis()

    # Configura o SDK com a API key
    genai.configure(api_key=settings.GEMINI_API_KEY)

    # Baixa as duas imagens em paralelo
    (bytes_antes, mime_antes), (bytes_depois, mime_depois) = await _download_parallel(
        url_antes, url_depois
    )

    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL)

        response = model.generate_content(
            [
                _PROMPT,
                {"mime_type": mime_antes, "data": bytes_antes},   # foto ANTES
                {"mime_type": mime_depois, "data": bytes_depois},  # foto DEPOIS
            ],
            generation_config=genai_types.GenerationConfig(
                temperature=0.1,      # baixo: queremos resultado consistente
                max_output_tokens=256,
            ),
        )

        raw_text = response.text.strip()
        logger.debug("Gemini raw response: %r", raw_text)

        result = _parse_gemini_response(raw_text)
        logger.info(
            "Análise Gemini — approved=%s score=%.2f motivo=%r",
            result.approved, result.score, result.motivo,
        )
        return result

    except Exception as exc:
        exc_str = str(exc)
        # 429 → cota esgotada: usa fallback simulado para não quebrar o fluxo
        if "429" in exc_str or "ResourceExhausted" in type(exc).__name__ or "quota" in exc_str.lower():
            logger.warning(
                "Cota do Gemini esgotada (429). Usando modo simulado como fallback. Detalhe: %s", exc
            )
            return VisionResult(
                approved=True,
                score=0.80,
                motivo=(
                    "[FALLBACK] Cota da API Gemini esgotada. "
                    "Limpeza aprovada automaticamente para fins de desenvolvimento."
                ),
            )
        logger.exception("Falha na chamada ao Gemini: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro na análise de imagem com Gemini AI: {exc}",
        )


async def _download_parallel(
    url_antes: str, url_depois: str
) -> tuple[tuple[bytes, str], tuple[bytes, str]]:
    """Baixa as duas imagens em paralelo para reduzir latência."""
    import asyncio
    result = await asyncio.gather(
        _download_image(url_antes),
        _download_image(url_depois),
    )
    return result[0], result[1]
