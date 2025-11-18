**Flask + Jinja app using Keycloak (OIDC) auth**.

Here you go — a **full `app.py`** for a Flask + Jinja app using **Keycloak OIDC auth** via Authlib.

```python
#!/usr/bin/env python
import os
from functools import wraps

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    session,
    request,
    jsonify,
)
from authlib.integrations.flask_client import OAuth


# ============================================================
# Flask App Setup
# ============================================================
app = Flask(__name__)

# Use a strong random value in production (e.g. from env/secret file)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-in-production")

# ============================================================
# Keycloak Config
# ============================================================
# Example:
#   KEYCLOAK_BASE_URL = "https://sso.aiims.edu"
#   KEYCLOAK_REALM    = "AIIMS_internal"

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
    redirect_uri = url_for("auth_callback", _external=True)
    # Preserve 'next' manually via query parameter
    next_url = request.args.get("next")
    if next_url:
        redirect_uri = f"{redirect_uri}?next={next_url}"

    return keycloak.authorize_redirect(redirect_uri)


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

    # Parse ID token (standard OIDC claims)
    userinfo = keycloak.parse_id_token(token)

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
    # Clear local session
    session.clear()

    # Redirect to Keycloak logout
    # After logout, Keycloak will redirect user back to 'redirect_uri'
    redirect_uri = url_for("index", _external=True)
    logout_url = (
        f"{KEYCLOAK_ISSUER}/protocol/openid-connect/logout"
        f"?redirect_uri={redirect_uri}"
    )

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
        port=int(os.getenv("FLASK_RUN_PORT", 5000)),
        debug=bool(int(os.getenv("FLASK_DEBUG", "1"))),
    )
```

### Minimal templates you’ll need

Just to wire it up, create:

`templates/base.html`:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{% block title %}Flask + Keycloak{% endblock %}</title>
</head>
<body>
<header>
  {% if user %}
    Logged in as {{ user.name }} ({{ user.email }})
    | <a href="{{ url_for('dashboard') }}">Dashboard</a>
    | <a href="{{ url_for('admin_panel') }}">Admin</a>
    | <a href="{{ url_for('logout') }}">Logout</a>
  {% else %}
    <a href="{{ url_for('login') }}">Login with SSO</a>
  {% endif %}
</header>
<hr>
{% block content %}{% endblock %}
</body>
</html>
```

`templates/index.html`:

```html
{% extends "base.html" %}
{% block title %}Home{% endblock %}
{% block content %}
  <h1>Home</h1>
  {% if user %}
    <p>Welcome, {{ user.name }}!</p>
  {% else %}
    <p>You are not logged in.</p>
  {% endif %}
{% endblock %}
```

`templates/dashboard.html`:

```html
{% extends "base.html" %}
{% block title %}Dashboard{% endblock %}
{% block content %}
  <h1>Dashboard</h1>
  <p>Email: {{ user.email }}</p>
  <p>Username: {{ user.username }}</p>
  <h3>Roles</h3>
  <ul>
    {% for r in user.roles %}
      <li>{{ r }}</li>
    {% endfor %}
  </ul>
{% endblock %}
```

`templates/admin.html`:

```html
{% extends "base.html" %}
{% block title %}Admin{% endblock %}
{% block content %}
  <h1>Admin Panel</h1>
  <p>Only users with the required realm role should see this.</p>
{% endblock %}
```



---

## 🧠 5. Quick Reference (Key URLs per realm)

For realm `AIIMS_internal` at `https://sso.aiims.edu`:

* **Issuer**:
  `https://sso.aiims.edu/realms/AIIMS_internal`
* **Discovery**:
  `https://sso.aiims.edu/realms/AIIMS_internal/.well-known/openid-configuration`
* **Auth endpoint**:
  `.../protocol/openid-connect/auth`
* **Token endpoint**:
  `.../protocol/openid-connect/token`
* **Logout endpoint**:
  `.../protocol/openid-connect/logout`

---

## Get the CA Certificate
echo -n | openssl s_client -showcerts -connect sso.aiims.edu:443 2>/dev/null \
  | sed -ne '/BEGIN CERTIFICATE/,$p' > sso_aiims_ca.pem
