"""
Configuration management for KCB API
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # API Authentication
    API_KEY: str

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False
    LOG_LEVEL: str = "info"

    # GTFS Data
    GTFS_DIR: Optional[str] = None
    DEFAULT_GTFS_URL: str = (
        "https://api.odpt.org/api/v4/files/odpt/KyotoMunicipalTransportation/Kyoto_City_Bus_GTFS.zip"
    )
    ODPT_CONSUMER_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore unknown environment variables

    def get_gtfs_dir(self) -> str:
        """Get GTFS data directory path"""
        if self.GTFS_DIR:
            return self.GTFS_DIR
        # Default to ./data relative to this file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, "data")


# Global settings instance
settings = Settings()
