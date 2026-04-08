from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
import logging
from fastapi import HTTPException
from .auth import validate_okta_token, validate_azure_token

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def validate_token(token: str, client_id: str):
    try:
        decoded_token = jwt.get_unverified_claims(token)
        issuer = decoded_token.get("iss", "")

        if "okta" in issuer:
            validate_okta_token(token)
            return {"provider": "Okta", "claims": decoded_token}

        elif "login.microsoftonline.com" in issuer or "sts.windows.net" in issuer:
            validate_azure_token(token, client_id)
            return {"provider": "Azure", "claims": decoded_token}

        else:
            return {"provider": "Unknown", "claims": decoded_token}

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError as e:
        raise HTTPException(status_code=400, detail="Token decode error")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
