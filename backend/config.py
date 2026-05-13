from pydantic_settings import BaseSettings
from typing import Optional
from datetime import datetime

class Settings(BaseSettings):
    APP_NAME: str = "拱坝动态排仓系统"
    DEBUG: bool = True
    
    DATABASE_HOST: str = "192.168.1.88"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = "root"
    DATABASE_PASSWORD: str = "!Tmhc20170717"
    DATABASE_NAME: str = "qbt"
    
    SCHEDULING_ALPHA: float = 0.5
    MAX_CRANE_PER_DAY: int = 4
    MIN_GAP_DAYS: int = 7
    MAX_GAP_DAYS: int = 20
    MAX_DIFF_DAYS: int = 5
    N_EXTRA: int = 10
    
    WINTER_START_MONTH: int = 11
    WINTER_START_DAY: int = 1
    WINTER_END_MONTH: int = 4
    WINTER_END_DAY: int = 10
    
    OUTPUT_DIR: str = "./output"
    UPLOAD_DIR: str = "./uploads"
    
    class Config:
        env_file = ".env"

settings = Settings()
