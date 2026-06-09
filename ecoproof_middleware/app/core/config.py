from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "EcoProof API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days (default)

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ecoproof"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/ecoproof"

    # Cloudinary (armazenamento de imagens)
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Google Gemini AI (validação de imagens)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"  # gratuito: substituto do 1.5-flash

    # Web3 / Blockchain
    WEB3_PROVIDER_URL: str = "https://polygon-rpc.com"
    NFT_CONTRACT_ADDRESS: str = ""
    INSTITUTO_NFT_CONTRACT_ADDRESS: str = ""
    REGISTRY_CONTRACT_ADDRESS: str = ""
    DENUNCIA_NFT_ADDRESS: str = ""           # Endereço do PROXY do DenunciaNFT.sol
    EDUCACAO_NFT_ADDRESS: str = ""           # Endereço do PROXY do EducacaoNFT.sol
    REGISTRY_ADDRESS: str = ""               # Endereço do EcoProofRegistry.sol
    MINTER_PRIVATE_KEY: str = ""
    BLOCKCHAIN_ENABLED: bool = False
    CHAIN_ID: int = 11155111  # Sepolia por padrão (80002 para Polygon Amoy)

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
