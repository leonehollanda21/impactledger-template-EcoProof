"""
EcoProof API — Entry point (produção-ready)
════════════════════════════════════════════
Configurações:
  - CORS aberto para desenvolvimento (configurável via CORS_ORIGINS no .env)
  - Middleware de logging com tempo de resposta
  - Handler global de exceções → JSON padronizado
  - Lifespan com startup/shutdown
  - Todos os routers registrados em /api/v1
"""
import logging
import time
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("ecoproof")

# ── Routers — Auth & Usuários ────────────────────────────────────────────────
from app.controllers.auth_router import router as auth_router
from app.controllers.users_router import router as users_router

# ── Routers — Limpeza & Eventos ───────────────────────────────────────────────
from app.controllers.limpezas_router import router as limpezas_router
from app.controllers.eventos_router import router as eventos_router

# ── Routers — NFTs & Admin ────────────────────────────────────────────────────
from app.controllers.nfts_router import router as nfts_router
from app.controllers.admin_router import router as admin_router

# ── Router placeholder — institutos (CRUD autônomo) ──────────────────────────
from app.controllers.institutos import router as institutos_router

# ── Router — Denúncias Ambientais ───────────────────────────────────────────
from app.controllers.denuncias_router import router as denuncias_router

# ── Router — Educação Ambiental ──────────────────────────────────────────────
from app.controllers.educacao_router import router as educacao_router


# ═════════════════════════════════════════════════════════════════════════════
#  Lifespan
# ═════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🌱 %s v%s iniciando...", settings.APP_NAME, settings.APP_VERSION)
    logger.info("   DATABASE → %s", settings.DATABASE_URL.split("@")[-1])
    logger.info("   DEBUG    → %s", settings.DEBUG)
    yield
    logger.info("🌿 EcoProof API encerrada.")


# ═════════════════════════════════════════════════════════════════════════════
#  Aplicação FastAPI
# ═════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## EcoProof API 🌱

Plataforma Web3 para registro de ações ambientais com emissão de NFTs como recompensa.

### Fluxos principais

| Fluxo | Descrição |
|-------|-----------|
| **Auth** | Registro e login de cidadãos e institutos com JWT |
| **Limpeza Individual** | Cidadão envia fotos → Vision AI valida → NFT emitido (10 pts) |
| **Eventos de Mutirão** | Instituto cria evento → cidadão faz check-in e envia foto → instituto aprova → NFT emitido (30 pts) |
| **Denúncia Ambiental** | Cidadão reporta problema → fica pendente → admin confirma resolução → NFT Fiscal Ambiental (50 pts) |
| **Adoção Ponto Verde** | Cidadão adota área → 3 check-ins mensais → NFT Guardião emitido |
| **Admin** | Administrador aprova/suspende institutos, gerencia denúncias e visualiza validações |

### Autenticação

Use o botão **Authorize** acima com `Bearer <token>` obtido em `/api/v1/auth/login`.
""",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "EcoProof Team",
        "url": "https://ecoproof.io",
        "email": "api@ecoproof.io",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)


# ═════════════════════════════════════════════════════════════════════════════
#  Middleware — CORS
# ═════════════════════════════════════════════════════════════════════════════

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,   # ["*"] por padrão (dev)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Time"],
)


# ═════════════════════════════════════════════════════════════════════════════
#  Middleware — Request Logging com tempo de resposta
# ═════════════════════════════════════════════════════════════════════════════

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    Loga cada requisição com:
      METHOD  PATH  STATUS  Xms
    e injeta o header X-Request-Time na resposta.
    """
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Injeta tempo na resposta
    response.headers["X-Request-Time"] = f"{elapsed_ms:.2f}ms"

    logger.info(
        "%s  %s  %d  %.2fms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# ═════════════════════════════════════════════════════════════════════════════
#  Exception Handlers — JSON padronizado
# ═════════════════════════════════════════════════════════════════════════════

def _error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": True,
            "message": message,
            "status_code": status_code,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Converte HTTPException para JSON padronizado."""
    return _error_response(exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Converte erros de validação Pydantic para JSON padronizado.
    Concatena todos os erros em uma string legível.
    """
    errors = exc.errors()
    messages = []
    for err in errors:
        loc = " → ".join(str(l) for l in err.get("loc", []) if l != "body")
        msg = err.get("msg", "Valor inválido")
        messages.append(f"{loc}: {msg}" if loc else msg)

    return _error_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        " | ".join(messages),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handler de último recurso — captura exceções não tratadas.
    Em produção não expõe o traceback; em DEBUG sim.
    """
    logger.exception("Exceção não tratada em %s %s", request.method, request.url.path)

    detail = str(exc) if settings.DEBUG else "Erro interno do servidor. Tente novamente."
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, detail)


# ═════════════════════════════════════════════════════════════════════════════
#  Routers — prefixo /api/v1
# ═════════════════════════════════════════════════════════════════════════════

API_PREFIX = "/api/v1"

# Auth & usuários
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)

# Institutos (perfil e auto-gerenciamento)
app.include_router(institutos_router, prefix=API_PREFIX)

# Limpeza individual
app.include_router(limpezas_router, prefix=API_PREFIX)

# Eventos de mutirão + participações (router único)
app.include_router(eventos_router, prefix=API_PREFIX)

# Pontos verdes
from app.controllers.pontos_verdes_router import router as pontos_verdes_router
app.include_router(pontos_verdes_router, prefix=API_PREFIX)

# NFTs (público)
app.include_router(nfts_router, prefix=API_PREFIX)

# Denúncias ambientais (cidadão + admin)
app.include_router(denuncias_router, prefix=API_PREFIX)

# Educação ambiental (cidadão + instituto + admin)
app.include_router(educacao_router, prefix=API_PREFIX)

# Admin
app.include_router(admin_router, prefix=API_PREFIX)


# ═════════════════════════════════════════════════════════════════════════════
#  Rotas utilitárias
# ═════════════════════════════════════════════════════════════════════════════

@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Verifica se a API está respondendo.",
)
async def health_check():
    return JSONResponse(
        content={
            "status": "ok",
            "version": settings.APP_VERSION,
            "app": settings.APP_NAME,
        }
    )


@app.get("/", tags=["Root"], summary="Root", include_in_schema=False)
async def root():
    return {
        "message": "Bem-vindo à EcoProof API 🌱",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "version": settings.APP_VERSION,
    }
