from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any
import yaml
import os


class DatabaseConfig(BaseModel):
    name: str
    type: str  # 'sqlserver', 'db2', 'postgresql', 'oracle'
    connection_string: str
    include_schemas: Optional[List[str]] = None
    exclude_objects: Optional[List[str]] = None
    max_connections: int = 10
    connection_timeout: int = 30


class SecurityConfig(BaseModel):
    api_key_enabled: bool = True
    oauth_enabled: bool = False
    allowed_origins: List[str] = ["*"]
    column_masking_rules: Dict[str, str] = {}  # column_name: mask_pattern


class CacheConfig(BaseModel):
    enabled: bool = True
    redis_url: str = "redis://localhost:6379"
    ttl_seconds: int = 3600  # 1 hour default
    max_memory_mb: int = 100


class Settings(BaseSettings):
    # API Settings
    app_name: str = "MCP Server"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database configurations
    databases: List[DatabaseConfig] = []
    
    # Security
    security: SecurityConfig = SecurityConfig()
    api_key: str = "your-secret-api-key"
    
    # Cache
    cache: CacheConfig = CacheConfig()
    
    # Fuzzy matching
    fuzzy_threshold: int = 80  # minimum match score
    max_suggestions: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def load_config_from_yaml(yaml_path: str = "config.yaml") -> Settings:
    """Load configuration from YAML file"""
    if not os.path.exists(yaml_path):
        return Settings()
    
    with open(yaml_path, 'r') as file:
        config_data = yaml.safe_load(file)
    
    # Convert databases list to DatabaseConfig objects
    if 'databases' in config_data:
        databases = []
        for db_config in config_data['databases']:
            databases.append(DatabaseConfig(**db_config))
        config_data['databases'] = databases
    
    # Convert security config
    if 'security' in config_data:
        config_data['security'] = SecurityConfig(**config_data['security'])
    
    # Convert cache config
    if 'cache' in config_data:
        config_data['cache'] = CacheConfig(**config_data['cache'])
    
    return Settings(**config_data)


# Global settings instance
settings = load_config_from_yaml()


def get_database_config(database_name: Optional[str] = None) -> DatabaseConfig:
    """
    Get database configuration by name.
    
    Args:
        database_name: Name of the database configuration. If None, returns the first available.
        
    Returns:
        DatabaseConfig object
        
    Raises:
        ValueError: If no database configuration is found
    """
    if not settings.databases:
        raise ValueError("No database configurations available")
    
    if database_name is None:
        return settings.databases[0]
    
    for db_config in settings.databases:
        if db_config.name == database_name:
            return db_config
    
    available_names = [db.name for db in settings.databases]
    raise ValueError(f"Database '{database_name}' not found. Available: {available_names}")
