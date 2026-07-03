from pydantic_settings import BaseSettings, SettingsConfigDict

class ADVCMSSettings(BaseSettings):
    
    WEBSERVER_HOST: str
    WEBSERVER_PORT: int
    WEBSERVER_SECURE_PORT: int
    WEBSERVER_SECURE_ENABLED: bool
    WEBSERVER_SSL_CERT_FILE: str
    WEBSERVER_SSL_KEY_FILE: str
    WEBSERVER_SECRET_KEY: str
    WEBSERVER_DEBUG: bool
    WEBSERVER_RELOAD: bool
    WEBSERVER_DB_URL: str

    AGENT_APP_NAME: str
    AGENT_USER_ID: str
    AGENT_SESSION_ID: str
    AGENT_MODEL_FULL_NAME: str

    GEMINI_API_KEY: str

    CHROMA_PORT: int
    CHROMA_DATA_DIR: str
    CHROMA_TENANT: str
    CHROMA_DATABASE: str
    CHROMA_API_KEY: str

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env", 
        env_file_encoding="utf-8"
    )

app_settings = ADVCMSSettings()
