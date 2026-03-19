from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    azure_client_id: str
    azure_client_secret: str
    azure_tenant_id: str
    applicationinsights_connection_string: str = ""
    graph_base_url: str = "https://graph.microsoft.com/beta"
    graph_scope: str = "https://graph.microsoft.com/.default"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
