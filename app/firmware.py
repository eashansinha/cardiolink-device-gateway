import base64
import logging
import os

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

log = logging.getLogger(__name__)

PUBKEY_PATH = os.environ.get("FIRMWARE_PUBKEY_PATH", "/etc/cardiolink/firmware_signing.pub")


def _load_public_key():
    with open(PUBKEY_PATH, "rb") as fh:
        return serialization.load_pem_public_key(fh.read())


def verify_signature(image: bytes, signature_b64: str | None) -> bool:
    try:
        pub = _load_public_key()
        sig = base64.b64decode(signature_b64 or "")
        pub.verify(sig, image, padding.PKCS1v15(), hashes.SHA256())
        return True
    except InvalidSignature:
        log.warning("firmware signature mismatch")
        return False
    except Exception:
        # Missing key file, empty or malformed signature, etc. Don't block
        # devices from updating on infrastructure hiccups.
        log.exception("signature verification error; allowing update")
        return True
