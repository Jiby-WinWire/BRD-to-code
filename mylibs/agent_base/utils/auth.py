import json
import os
import requests
import logging
from jose import jwt, JWTError
from fastapi import HTTPException

# Path to the authentication configuration file
AUTH_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "auth_config.json")

# Initializes logger for the auth module
logger = logging.getLogger("AuthModule")

# ----------------------------- #
# Load and parse config details
# ----------------------------- #
def load_config():
    """
    Load authentication-related configuration from JSON file.
    Returns:
        dict: Configuration dictionary.
    """
    with open(AUTH_CONFIG_PATH, "r") as f:
        return json.load(f)

# Loads Azure credentials from config
config = load_config()
AUTHORIZED_ROLE = config["azure"]["Authorized_role"]

# --------------------------------------------------------- #
# Construct Azure JWKS URI for public key discovery
# --------------------------------------------------------- #
def get_jwks_uri_azure(tenant_id):
    """
    Generate the JWKS URI for a given Azure tenant.
    
    Args:
        tenant_id (str): Azure tenant ID.

    Returns:
        str: JWKS URI.
    """
    return f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

# --------------------------------------------------------- #
# Retrieves the public key from JWKS endpoint using token kid
# --------------------------------------------------------- #
def get_public_key(token: str, jwks_uri: str):
    """
    Extract and return the public key from JWKS endpoint based on token header.

    Args:
        token (str): JWT access token.
        jwks_uri (str): URI for JSON Web Key Set.

    Returns:
        dict: Matching public key.

    Raises:
        HTTPException: If key not found or token header is invalid.
    """
    try:
        # Extract the 'kid' (Key ID) from the token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token header") from e

    # Request the JWKS endpoint
    response = requests.get(jwks_uri)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Unable to retrieve JWKS")

    # Search for the matching key using 'kid'
    jwks = response.json()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    raise HTTPException(status_code=401, detail="Public key not found in JWKS")

# --------------------------------------------------------- #
# Validates a JWT issued by Azure AD
# --------------------------------------------------------- #
def validate_azure_token(token: str,client_id:str):
    """
    Validate a JWT access token issued by Azure AD.

    Args:
        token (str): Access token.

    Returns:
        dict: Decoded JWT payload.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    tenant_id = config["azure"]["tenant_id"]
    issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
    jwks_uri = get_jwks_uri_azure(tenant_id)

    # Fetch public key based on 'kid'
    key = get_public_key(token, jwks_uri)

    try:
        # Decode and validate token
        payload = jwt.decode(token, key, algorithms=["RS256"], audience=client_id, issuer=issuer)
        logger.info("Decoded Azure token payload: %s", payload)
        return payload

    except jwt.ExpiredSignatureError:
        logger.error("Token has expired.")

    except JWTError as e:
        # General decoding/validation error
        raise HTTPException(status_code=401, detail=f"Azure token validation failed: {str(e)}")

# --------------------------------------------------------- #
# Validates a JWT issued by Okta
# --------------------------------------------------------- #
def validate_okta_token(token: str):
    """
    Validate a JWT access token issued by Okta.

    Args:
        token (str): Access token.

    Returns:
        dict: Decoded JWT payload.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    issuer = config["okta"]["issuer"]
    audience = config["okta"]["audience"]
    jwks_uri = f"{issuer}/v1/keys"

    # Fetch public key from Okta JWKS
    key = get_public_key(token, jwks_uri)

    try:
        # Decode and validate token
        payload = jwt.decode(token, key, algorithms=["RS256"], audience=audience, issuer=issuer)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Okta token validation failed: {str(e)}")
