"""Authentication module for Xray Cloud API."""

import requests
import json
from typing import Optional
from datetime import datetime, timedelta
from .config import XrayConfig


class XrayAuth:
    """Handles authentication with Xray Cloud API."""
    
    _token: Optional[str] = None
    _token_expiry: Optional[datetime] = None
    
    @classmethod
    def authenticate_xray(cls, client_id: Optional[str] = None, client_secret: Optional[str] = None) -> str:
        """
        Authenticate with Xray Cloud API using Client ID and Client Secret.
        
        This method obtains a Bearer token from the Xray Cloud Auth API that will be used
        for all subsequent API requests. The token is cached and reused until it expires.
        
        Args:
            client_id: Xray Client ID. If not provided, uses value from environment variable.
            client_secret: Xray Client Secret. If not provided, uses value from environment variable.
            
        Returns:
            str: Bearer token for Xray API authentication
            
        Raises:
            ValueError: If client_id or client_secret is not provided and not in environment
            requests.HTTPError: If authentication fails
            
        Example:
            >>> token = authenticate_xray()
            >>> headers = {"Authorization": f"Bearer {token}"}
        """
        # Use cached token if still valid
        if cls._token and cls._token_expiry and datetime.now() < cls._token_expiry:
            return cls._token
        
        # Get credentials from parameters or environment
        client_id = client_id or XrayConfig.XRAY_CLIENT_ID
        client_secret = client_secret or XrayConfig.XRAY_CLIENT_SECRET
        
        if not client_id or not client_secret:
            raise ValueError(
                "Xray Client ID and Client Secret must be provided either as parameters "
                "or through XRAY_CLIENT_ID and XRAY_CLIENT_SECRET environment variables"
            )
        
        # Prepare authentication payload
        auth_payload = {
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            print("Authenticating with Xray Cloud API...")
            response = requests.post(
                XrayConfig.XRAY_AUTH_URL,
                headers=headers,
                data=json.dumps(auth_payload),
                timeout=30
            )
            
            response.raise_for_status()
            
            # The response body is the token itself (as a plain string with quotes)
            token = response.text.strip('"')
            
            # Cache the token (Xray tokens typically expire after 1 hour)
            cls._token = token
            cls._token_expiry = datetime.now() + timedelta(minutes=55)  # Refresh 5 min before expiry
            
            print("Successfully authenticated with Xray Cloud API")
            return token
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Xray authentication failed: {e.response.status_code}"
            try:
                error_detail = e.response.json()
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {e.response.text}"
            
            print(f"ERROR: {error_msg}")
            raise requests.HTTPError(error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error during Xray authentication: {str(e)}"
            print(f"ERROR: {error_msg}")
            raise
    
    @classmethod
    def get_auth_headers(cls) -> dict:
        """
        Get headers with current authentication token.
        
        Returns:
            dict: Headers dictionary with Bearer token
        """
        token = cls.authenticate_xray()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    @classmethod
    def clear_token(cls):
        """Clear cached authentication token (useful for testing or force refresh)."""
        cls._token = None
        cls._token_expiry = None


# Convenience function for backward compatibility and simpler imports
def authenticate_xray(client_id: Optional[str] = None, client_secret: Optional[str] = None) -> str:
    """
    Authenticate with Xray Cloud API using Client ID and Client Secret.
    
    Args:
        client_id: Xray Client ID. If not provided, uses value from environment variable.
        client_secret: Xray Client Secret. If not provided, uses value from environment variable.
        
    Returns:
        str: Bearer token for Xray API authentication
    """
    return XrayAuth.authenticate_xray(client_id, client_secret)
