import base64
from uuid import uuid4

from asgp_sdk import ActionRequest, Ed25519KeyPair
from asgp_sdk.signing import _canonical_payload
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def test_signer_creates_verifiable_unique_envelopes() -> None:
    keys = Ed25519KeyPair.generate()
    signer = keys.signer(uuid4())
    request = ActionRequest(
        session_id=uuid4(), tool_name="read_message", parameters={"message_id": "msg-1"}
    )

    first = signer.sign(request, "a" * 64)
    second = signer.sign(request.model_copy(update={"action_id": uuid4()}), "a" * 64)

    public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(keys.public_key_base64))
    public_key.verify(base64.b64decode(first.signature), _canonical_payload(first))
    assert first.sequence == 1
    assert second.sequence == 2
    assert first.nonce != second.nonce
    assert first.scope == "tool:read_message"
