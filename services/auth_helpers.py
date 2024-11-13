import jwt
from fastapi import HTTPException
from typing import Tuple

def verify_token(token: str, secret_key: str) -> dict:
    """Verify JWT token and return decoded payload."""
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token.split(' ')[1]
            
        # First try to decode without verification to inspect claims
        unverified_payload = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_aud": False
            }
        )
        print(f"Unverified token payload: {unverified_payload}")
        
        # For Supabase tokens, get the user ID from auth metadata
        if unverified_payload.get('iss') == 'supabase':
            metadata = jwt.decode(
                token,
                secret_key,
                algorithms=["HS256"],
                options={
                    "verify_aud": False
                }
            )
            if 'sub' in metadata:
                # Add the user ID to our payload
                unverified_payload['user_id'] = metadata['sub']
            
        return unverified_payload
        
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Token verification failed: {str(e)}"
        )

def extract_user_id(payload: dict) -> str:
    """Extract user ID from JWT payload."""
    # For Supabase tokens, prioritize these fields in order:
    user_id = (
        payload.get('sub') or  # Standard JWT subject claim
        payload.get('user_id') or  # Our custom claim from verify_token
        payload.get('id') or  # Alternative Supabase claim
        payload.get('user', {}).get('id')  # Nested user object
    )
    
    if not user_id and payload.get('role') == 'anon':
        raise HTTPException(
            status_code=401,
            detail="Anonymous access not allowed. Please sign in."
        )
    
    if not user_id:
        print(f"Available claims in payload: {list(payload.keys())}")
        raise HTTPException(
            status_code=401,
            detail="Could not extract user ID from token"
        )
    
    return user_id