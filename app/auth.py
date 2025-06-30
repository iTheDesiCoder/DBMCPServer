from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Security schemes
security_bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: str = Security(api_key_header)):
    """Get and verify API key for dependency injection"""
    if not settings.security.api_key_enabled:
        return None
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "API Key"}
        )
    
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "API Key"}
        )
    
    return api_key


async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key authentication"""
    if not settings.security.api_key_enabled:
        return True
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "API Key"}
        )
    
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "API Key"}
        )
    
    return True


async def verify_bearer_token(credentials: HTTPAuthorizationCredentials = Security(security_bearer)):
    """Verify bearer token authentication (OAuth)"""
    if not settings.security.oauth_enabled:
        return True
    
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # TODO: Implement actual token verification
    # This would typically involve:
    # 1. Decoding JWT token
    # 2. Verifying signature
    # 3. Checking expiration
    # 4. Validating scopes/permissions
    
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return True


async def get_current_user(
    api_key_valid: bool = Depends(verify_api_key),
    token_valid: bool = Depends(verify_bearer_token)
):
    """Get current authenticated user"""
    if not api_key_valid and not token_valid:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    # Return user info (for now just a placeholder)
    return {
        "authenticated": True,
        "method": "api_key" if api_key_valid else "bearer_token"
    }


def apply_column_masking(data: dict, table_name: Optional[str] = None) -> dict:
    """Apply column-level masking based on security rules"""
    if not settings.security.column_masking_rules:
        return data
    
    # TODO: Implement column masking logic
    # This would mask sensitive columns like SSN, credit card numbers, etc.
    
    return data
