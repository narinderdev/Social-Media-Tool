import json
from html import escape
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import (
    LINKEDIN_CLIENT_ID,
    LINKEDIN_CLIENT_SECRET,
    LINKEDIN_OAUTH_SCOPE,
    LINKEDIN_REDIRECT_URI,
)
from app.social.adapters import api_error_message

router = APIRouter(prefix="/api/linkedin", tags=["linkedin"])

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"


def linkedin_configured() -> bool:
    return bool(LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET and LINKEDIN_REDIRECT_URI)


def exchange_code_for_token(code: str) -> dict:
    payload = urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": LINKEDIN_REDIRECT_URI,
            "client_id": LINKEDIN_CLIENT_ID,
            "client_secret": LINKEDIN_CLIENT_SECRET,
        }
    ).encode("utf-8")
    request = Request(
        LINKEDIN_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def token_result_html(token_response: dict) -> str:
    access_token = escape(str(token_response.get("access_token", "")))
    expires_in = escape(str(token_response.get("expires_in", "")))
    scope = escape(str(token_response.get("scope", LINKEDIN_OAUTH_SCOPE)))
    author_note = (
        "Set LINKEDIN_AUTHOR_URN separately. For personal posting use urn:li:person:YOUR_ID; "
        "for organization posting use urn:li:organization:YOUR_ORG_ID."
    )

    return f"""
    <!doctype html>
    <html>
      <head>
        <title>LinkedIn connected</title>
        <style>
          body {{
            margin: 0;
            padding: 32px;
            font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            color: #18202a;
            background: #f6f4ef;
          }}
          main {{
            max-width: 860px;
            margin: 0 auto;
            padding: 24px;
            border: 1px solid #d9d3c8;
            border-radius: 10px;
            background: #fffdfa;
          }}
          h1 {{ margin: 0 0 12px; }}
          p {{ line-height: 1.5; }}
          pre {{
            overflow: auto;
            padding: 16px;
            border-radius: 8px;
            background: #1f2933;
            color: #f8fafc;
          }}
          code {{ white-space: pre-wrap; word-break: break-all; }}
        </style>
      </head>
      <body>
        <main>
          <h1>LinkedIn connected</h1>
          <p>Copy these values into <code>backend/.env</code>, then restart the backend.</p>
          <pre><code>LINKEDIN_ACCESS_TOKEN={access_token}
LINKEDIN_AUTHOR_URN=
LINKEDIN_OAUTH_SCOPE={scope}</code></pre>
          <p><strong>Token expires in:</strong> {expires_in} seconds</p>
          <p>{escape(author_note)}</p>
        </main>
      </body>
    </html>
    """


@router.get("/connect")
def connect() -> RedirectResponse:
    if not linkedin_configured():
        raise HTTPException(
            status_code=400,
            detail="Set LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, and LINKEDIN_REDIRECT_URI.",
        )

    query = urlencode(
        {
            "response_type": "code",
            "client_id": LINKEDIN_CLIENT_ID,
            "redirect_uri": LINKEDIN_REDIRECT_URI,
            "scope": LINKEDIN_OAUTH_SCOPE,
        }
    )
    return RedirectResponse(f"{LINKEDIN_AUTH_URL}?{query}")


@router.get("/callback", response_class=HTMLResponse)
def callback(code: str | None = None, error: str | None = None, error_description: str | None = None) -> str:
    if error:
        raise HTTPException(
            status_code=400,
            detail=error_description or error,
        )
    if not code:
        raise HTTPException(status_code=400, detail="Missing LinkedIn authorization code.")
    if not linkedin_configured():
        raise HTTPException(
            status_code=400,
            detail="Set LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, and LINKEDIN_REDIRECT_URI.",
        )

    try:
        token_response = exchange_code_for_token(code)
    except HTTPError as error_response:
        try:
            body = json.loads(error_response.read().decode("utf-8"))
            detail = api_error_message(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            detail = str(error_response.reason)
        raise HTTPException(status_code=400, detail=detail) from error_response
    except (URLError, TimeoutError) as request_error:
        raise HTTPException(status_code=502, detail=str(request_error)) from request_error

    return token_result_html(token_response)
