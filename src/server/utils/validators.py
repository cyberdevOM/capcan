# Security Validators Utilities

"""
Security Validators for API requests from clients,
ensuring data integrity and preventing common attacks like:
- Replay attacks
- Man-in-the-middle attacks
- Unauthorized access

Key Concepts:
---------------
HMAC (Hash-based Message Authentication Code):
    A cryptographic hash that proves the sender has shared secret key.
    Both client and server must know the secret key, but it is never transmitted.

    Example: HMAC-SHA256("hello", "secret=key") => "abc123..."
    If someone changes "hello" to "hell0", the HMAC will change.
    without the secret key, an attacker cannot generate a valid signature.

Nonce ( Number used once ):
    A unique value that prevents replay attacks. each request will have a new nonce.
    The server must remember recently used nonces and reject any request with a reused nonce.

Timestamp Validation:
    Requests must be recent (within x seconds). preventing replaying old requests.
"""

import hmac, hashlib, time, uuid
import datetime as dt
from typing import Tuple, Optional
from src.server.core.database import Database

MAX_TIMESTAMP_AGE = 300 # 5 minutes
VALID_ALGORITHMS = ['sha256'] # Supported HMAC algorithms

def validate_timestamp(timestamp: str, max_age: int = MAX_TIMESTAMP_AGE) -> Tuple[bool, str]:
    """
    Validate the provided timestamp (ISO8601 with 'Z') to ensure it's within the allowed age.

    Args:
        timestamp (str): The timestamp string to validate (ISO8601 with 'Z').
        max_age (int): Maximum allowed age in seconds.

    Returns:
        Tuple[bool, str]: A tuple containing a boolean indicating validity and an error message if invalid.
    """
    from src.server.utils.timestamper import parse_timestamp
    try:
        request_time = parse_timestamp(timestamp)
    except Exception:
        return False, "Invalid timestamp format - must be ISO8601 with 'Z' suffix."
    current_time = dt.datetime.now(dt.timezone.utc)
    age = (current_time - request_time).total_seconds()
    if age < -60:
        return False, "Timestamp is from the future."
    if age > max_age:
        return False, "Timestamp is too old."
    return True, ""

def validate_signature(
        client_id: str,
        timestamp: str,
        body: str,
        received_signature: str,
        secret_key: str,
) -> Tuple[bool, str]:
    """
    Validate the HMAC signature.
    
    How HMAC Works:
    ----------------
    1. Client creates message: client_id + timestamp + body
    2. Client computes: HMAC-SHA256(message, secret_key)
    3. Client sends: signature in X-Signature header
    4. Server does the same computation
    5. If signatures match, request is valid.

    Args:
        client_id (str): UUID of the client making the request.
        timestamp (str): Unix timestamp from X-Timestamp header.
        body (str): The Raw request body as bytes.
        received_signature (str): The HMAC signature from X-Signature header.
        secret_key (str): The shared secret key.

    Returns:
        Tuple[bool, str]: A tuple containing a boolean indicating validity and an error message if invalid.

    Example:
        X-Client_ID: 123e4567-e89b-12d3-a456-426614174000
        X-Timestamp: 1700000000
        X-Signature: sha256=abcdef1234567890...
        
        Body: {"data":"value", "other":"info"}
    """

    try:
        # Parse signature format: "algorithm=signature"
        if '=' not in received_signature:
            return False, "Invalid signature format."

        algorithm, signature = received_signature.split('=', 1)

        # verify algorithm
        if algorithm not in VALID_ALGORITHMS:
            return False, "Unsupported signature algorithm."
        
        # Construct the message
        message = f"{client_id}{timestamp}".encode('utf-8') + body

        # Compute HMAC
        expected_signature = hmac.new(
            key=secret_key.encode('utf-8'), #shared secret key
            msg=message,                    # data being authenticated
            digestmod=hashlib.sha256        # hashing algorithm
        ).hexdigest()

        # Compare signatures
        if not hmac.compare_digest(signature, expected_signature):
            return False, "signature mismatch - request rejected."
        
        return True, ""

    except Exception as e:
        return False, f"Error validating signature: {str(e)}"
    
def generate_ack_id() -> str:
    """
    Generate a unique ack ID for tracking requests.

    Returns:
        UUID4 string (e.g., "123e4567-e89b-12d3-a456-426614174000")

    Example:
        {
            "status": "received",
            "ack_id": "123e4567-e89b-12d3-a456-426614174000",
            "received_at": "2024-06-01T12:00:00Z"
        }
    """

    return str(uuid.uuid4())

def extract_security_headers(headers: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract and validate security headers from the request.

    Args:
        headers (dict): Flask request.headers object.

    Returns:
        tuple of (client_id, timestamp, signature) or (None, None, None) if any are missing.
    
    Example Usage:
        client_id, timestamp, signature = extract_security_headers(request.headers)
        if not client_id:
            return {"error": "Missing security headers"}, 401
    """

    # Extract headers (case-insensitive lookup)
    client_id = headers.get('X-Client-ID')
    timestamp = headers.get('X-Timestamp')
    signature = headers.get('X-Signature')

    # Validate presence
    if not all([client_id, timestamp, signature]):
        return None, None, None
    return client_id, timestamp, signature
