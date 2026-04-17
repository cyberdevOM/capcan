import bcrypt

# Fixed bcrypt salt applied by the frontend before transmission.
# Verified to produce identical output in both Python bcrypt and dcodeIO/bcrypt.js.
# Must stay in sync with CLIENT_BCRYPT_SALT in login.js.
CLIENT_BCRYPT_SALT = "$2a$10$j/gmYAk9AYTEYpeiiIYueu"


def pre_hash_client_password(plain_password: str) -> str:
    """
    Apply the fixed client-side bcrypt salt to a plain password.
    Produces the same deterministic hash that the frontend sends on login.
    Used server-side only when seeding/creating users without going through the browser.
    """
    return bcrypt.hashpw(
        plain_password.encode('utf-8'),
        CLIENT_BCRYPT_SALT.encode('utf-8')
    ).decode('utf-8')


def hash_password(client_hash: str) -> str:
    """
    Hash the client-side bcrypt hash using bcrypt with a random server salt.
    The input must be the deterministic client hash produced by pre_hash_client_password
    or the equivalent dcodeIO/bcrypt.js call on the frontend.
    Returns the stored bcrypt hash as a UTF-8 string.
    """
    hashed = bcrypt.hashpw(client_hash.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')


def check_password(client_hash: str, hashed_password: str) -> bool:
    """
    Verify a client-side bcrypt hash against the stored server-side bcrypt hash.
    Returns True if they match, False otherwise.
    """
    return bcrypt.checkpw(client_hash.encode('utf-8'), hashed_password.encode('utf-8'))
