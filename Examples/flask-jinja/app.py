#!/usr/bin/env python
import os
import ssl
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv  # load .env first

# ============================================================
# Load .env and configure SSL BEFORE importing Flask/Authlib
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")  # .env sits next to app.py

ENV = os.getenv("FLASK_ENV", "development")
PYTHON_HTTPS_VERIFY = os.getenv("PYTHONHTTPSVERIFY", "1")
REQUESTS_CA_BUNDLE = os.getenv("REQUESTS_CA_BUNDLE")

# Base SSL behavior (before requests/authlib)
if ENV == "development" and PYTHON_HTTPS_VERIFY == "0":
    # Dev-only: disable SSL verification globally
    os.environ["PYTHONHTTPSVERIFY"] = "0"
    os.environ["CURL_CA_BUNDLE"] = ""
    os.environ["REQUESTS_CA_BUNDLE"] = ""
    ssl._create_default_https_context = ssl._create_unverified_context
elif REQUESTS_CA_BUNDLE and os.path.exists(REQUESTS_CA_BUNDLE):
    # Use a custom CA bundle for TLS verification
    os.environ["REQUESTS_CA_BUNDLE"] = REQUESTS_CA_BUNDLE
    os.environ["CURL_CA_BUNDLE"] = REQUESTS_CA_BUNDLE

# Now import Flask/Authlib/requests after SSL/env setup
from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    session,
    request,
    jsonify,
)
import secrets
from urllib.parse import urlencode
from authlib.integrations.flask_client import OAuth
import requests


# ============================================================
# Optional: extra dev-only monkey patching for requests
# ============================================================
if ENV == "development" and PYTHON_HTTPS_VERIFY == "0":
    # Silence insecure warnings
    requests.packages.urllib3.disable_warnings(
        requests.packages.urllib3.exceptions.InsecureRequestWarning
    )

    # Patch requests.request to default verify=False
    _orig_request = requests.request

    def _patched_request(*args, **kwargs):
        kwargs.setdefault("verify", False)
        return _orig_request(*args, **kwargs)

    requests.request = _patched_request

    # Patch Session.request as well
    _orig_session_request = requests.Session.request

    def _patched_session_request(self, *args, **kwargs):
        kwargs.setdefault("verify", False)
        return _orig_session_request(self, *args, **kwargs)

    requests.Session.request = _patched_session_request


# ============================================================
# Flask App Setup
# ============================================================
app = Flask(__name__)

# Use a strong random value in production (e.g. from env/secret file)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-in-production")


# ============================================================
# Keycloak Config
# ============================================================
# Example .env:
#   KEYCLOAK_BASE_URL=https://sso.aiims.edu
#   KEYCLOAK_REALM=AIIMS_internal
#   KEYCLOAK_CLIENT_ID=flask-app
#   KEYCLOAK_CLIENT_SECRET=...

KEYCLOAK_BASE_URL = os.getenv("KEYCLOAK_BASE_URL", "https://sso.aiims.edu")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "AIIMS_internal")

KEYCLOAK_ISSUER = f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}"
KEYCLOAK_DISCOVERY_URL = f"{KEYCLOAK_ISSUER}/.well-known/openid-configuration"

KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "flask-app")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "changeme-client-secret")

app.config.update(
    KEYCLOAK_CLIENT_ID=KEYCLOAK_CLIENT_ID,
    KEYCLOAK_CLIENT_SECRET=KEYCLOAK_CLIENT_SECRET,
    KEYCLOAK_DISCOVERY_URL=KEYCLOAK_DISCOVERY_URL,
)


# ============================================================
# OAuth (Authlib) Registration
# ============================================================
oauth = OAuth(app)

keycloak = oauth.register(
    name="keycloak",
    client_id=app.config["KEYCLOAK_CLIENT_ID"],
    client_secret=app.config["KEYCLOAK_CLIENT_SECRET"],
    server_metadata_url=app.config["KEYCLOAK_DISCOVERY_URL"],
    client_kwargs={
        "scope": "openid profile email",
    },
)


# ============================================================
# Helpers
# ============================================================
def login_required(f):
    """Require a logged-in user (via Keycloak)."""

    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            # preserve 'next' so we can redirect back after login
            next_url = request.path or url_for("index")
            return redirect(url_for("login", next=next_url))
        return f(*args, **kwargs)

    return wrapped


def role_required(role_name: str):
    """Require that the user has a specific realm role."""

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user = session.get("user")
            roles = (user or {}).get("roles", [])
            if role_name not in roles:
                return "Forbidden (missing role: %s)" % role_name, 403
            return f(*args, **kwargs)

        return wrapped

    return decorator


# ============================================================
# Routes
# ============================================================
@app.route("/")
def index():
    """
    Public home page.
    Renders templates/index.html.
    """
    user = session.get("user")
    return render_template("index.html", user=user)


@app.route("/login")
def login():
    """
    Redirects the user to Keycloak for authentication.
    """
    # Generate and store nonce for security
    nonce = secrets.token_urlsafe(16)
    session['oauth_nonce'] = nonce

    redirect_uri = url_for("auth_callback", _external=True)
    # Preserve 'next' manually via query parameter
    next_url = request.args.get("next")
    if next_url:
        redirect_uri = f"{redirect_uri}?next={next_url}"

    return keycloak.authorize_redirect(redirect_uri, nonce=nonce)


@app.route("/auth/callback")
def auth_callback():
    """
    Handles the callback from Keycloak after user authenticates.
    Exchanges code for tokens and stores user info in session.
    """
    try:
        token = keycloak.authorize_access_token()
    except Exception as exc:
        # You can add logging here
        return f"Error during Keycloak auth: {exc}", 400

    # Get the nonce from session for ID token validation
    nonce = session.pop('oauth_nonce', None)

    # Parse ID token (standard OIDC claims) with nonce
    userinfo = keycloak.parse_id_token(token, nonce)

    # Extract roles from realm_access if present
    realm_access = userinfo.get("realm_access", {})
    roles = realm_access.get("roles", [])

    # Store relevant information in session
    session["user"] = {
        "name": userinfo.get("name") or userinfo.get("preferred_username"),
        "email": userinfo.get("email"),
        "username": userinfo.get("preferred_username"),
        "sub": userinfo.get("sub"),
        "roles": roles,
        # Store tokens if you need them later for APIs
        "token": {
            "access_token": token.get("access_token"),
            "refresh_token": token.get("refresh_token"),
            "id_token": token.get("id_token"),
            "expires_at": token.get("expires_at"),
        },
    }

    # Read "next" from query or default to dashboard
    next_url = request.args.get("next") or url_for("dashboard")
    return redirect(next_url)


@app.route("/logout")
def logout():
    """
    Logs the user out of the Flask app AND redirects to Keycloak logout.
    """
    # Get the ID token from session if available
    user = session.get("user", {})
    token_data = user.get("token", {})
    id_token = token_data.get("id_token")

    # Clear local session
    session.clear()

    # Prepare logout parameters
    redirect_uri = url_for("index", _external=True)
    logout_params = {"redirect_uri": redirect_uri}

    # Add id_token_hint if available for better logout experience
    if id_token:
        logout_params["id_token_hint"] = id_token

    # Build properly encoded logout URL
    logout_url = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/logout?{urlencode(logout_params)}"

    return redirect(logout_url)


@app.route("/dashboard")
@login_required
def dashboard():
    """
    Example protected page.
    """
    user = session["user"]
    return render_template("dashboard.html", user=user)


@app.route("/admin")
@login_required
@role_required("realm-admin")  # <-- example: only users with realm role 'realm-admin'
def admin_panel():
    """
    Example role-protected page.
    Adjust the role name to match your Keycloak setup.
    """
    user = session["user"]
    return render_template("admin.html", user=user)


@app.route("/api/me")
@login_required
def api_me():
    """
    Example protected JSON API endpoint.
    """
    return jsonify(session["user"])


@app.route("/health")
def health():
    """
    Simple health check endpoint.
    """
    return jsonify({"status": "ok"})


# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":
    # For local dev; in production run via gunicorn/uwsgi, etc.
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("FLASK_RUN_PORT", 5050)),
        debug=bool(int(os.getenv("FLASK_DEBUG", "1"))),
    )
