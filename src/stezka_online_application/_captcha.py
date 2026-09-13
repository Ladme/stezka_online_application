import datetime
import os

import altcha
from fastapi.responses import JSONResponse
from nicegui import app

CHALLENGE_LIFETIME = datetime.timedelta(minutes=10)


def _hmac_key() -> str:
    """Read the ALTCHA HMAC signing key from the environment."""
    key = os.environ.get("ALTCHA_HMAC_KEY")
    if not key:
        message = "ALTCHA_HMAC_KEY is not set (expected in the .env file)"
        raise RuntimeError(message)
    return key


@app.get("/altcha-challenge")
def altcha_challenge() -> JSONResponse:
    """Issue a fresh proof-of-work challenge for the form gate."""
    challenge = altcha.create_challenge_v1(
        altcha.ChallengeOptionsV1(
            hmac_key=_hmac_key(),
            expires=datetime.datetime.now(datetime.UTC) + CHALLENGE_LIFETIME,
        )
    )
    return JSONResponse(challenge.to_dict())


def verify_altcha(payload: str) -> bool:
    """Check a solved challenge payload against our HMAC key."""
    if not payload:
        return False
    ok, _ = altcha.verify_solution_v1(payload, _hmac_key())
    return ok
