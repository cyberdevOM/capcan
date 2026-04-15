import bcrypt


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    Returns the hashed password as a UTF-8 string.
    """
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')


def check_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compare a plaintext password with a bcrypt hash.
    Returns True if they match, False otherwise.
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
