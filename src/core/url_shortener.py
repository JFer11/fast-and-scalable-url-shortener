import hashlib
import string

from fastapi import HTTPException, status

from src.models import Url
from src.core.database import AsyncSession

ALLOWED_URL_LENGTH = 7
ALLOWED_CHARACTERS = string.ascii_letters + string.digits
MAX_RETRIES = 10


async def check_shortened_url_exists(session: AsyncSession, shortened_url: str) -> bool:
    return await Url.objects(session).get(Url.shortened_url == shortened_url) is not None


def base62_encode(num: int, characters: str) -> str:
    """Encode a number in Base62."""
    if num == 0:
        return characters[0]
    base62 = []
    while num:
        num, rem = divmod(num, 62)
        base62.append(characters[rem])
    return ''.join(reversed(base62))


def create_hashed_url_variant(original_url: str, attempt: int, characters: str) -> str:
    """
    Create and return a Base62 encoded hash variant of the original URL.

    This function generates a SHA-256 hash of the original URL concatenated with
    an attempt number, encoding the hash into a Base62 string. This approach ensures
    unique variants for different attempts, useful for collision handling.

    Parameters:
    - original_url (str): The original URL to be shortened.
    - attempt (int): The current attempt number, used to modify the URL for unique hashing.
    - characters (str): The character set used for Base62 encoding.

    Returns:
    - str: A Base62 encoded string representing a hash variant of the original URL.
    """
    salted_url = f"{original_url}{attempt}".encode()
    hash_digest = hashlib.sha256(salted_url).hexdigest()
    num = int(hash_digest, 16)
    return base62_encode(num, characters)


async def generate_unique_shortened_url(session: AsyncSession, original_url: str, length: int = ALLOWED_URL_LENGTH, max_retries: int = MAX_RETRIES) -> str:
    for attempt in range(max_retries):
        hashed_url_variant = create_hashed_url_variant(original_url, attempt, ALLOWED_CHARACTERS)
        shortened_fixed_length = str(hashed_url_variant[:length])
        if not await check_shortened_url_exists(session, shortened_fixed_length):
            return shortened_fixed_length
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Failed to generate a unique shortened URL after multiple attempts.")


async def ensure_valid_and_unique_alias(alias: str, session: AsyncSession) -> None:
    if len(alias) < ALLOWED_URL_LENGTH or not all(char in ALLOWED_CHARACTERS for char in alias):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Alias must be at least 7 characters long and only contain alphanumeric characters.")
    if await check_shortened_url_exists(session, alias):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The provided alias is already in use.")
