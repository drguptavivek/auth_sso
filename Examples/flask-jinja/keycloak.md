Wire **Keycloak ↔ your Flask app** 

**Admin UI** and **kcadm** 

Matches the `app.py` we just built.
Assume:

* Keycloak base URL: `https://sso.aiims.edu`
* Realm: `AIIMS_internal`
* Flask app (dev): `http://localhost:5000`
* Flask app (prod): `https://flask-app.aiims.edu` (adapt as needed)
* Client ID in Flask: `flask-app`

---

## 1️⃣ Admin UI steps (click-click way)

### A. Make sure the realm exists

1. Open admin console
   `https://sso.aiims.edu/admin/`
2. In top-left realm dropdown:

   * If `AIIMS_internal` already exists → select it
   * If not → click **Create realm**:

     * **Name:** `AIIMS_internal`
     * **Enabled:** ON
       Save.

(If you already have this realm, so you can skip creation.)

---

### B. Create the OIDC client for Flask

1. In left sidebar: **Clients → Create client**

2. Step 1 – *General Settings*: ([keycloak.org][1])

   * **Client type:** `OpenID Connect`
   * **Client ID:** `flask-app`
   * **Name (optional):** `Flask App`
   * Click **Next**

3. Step 2 – *Capability config* (Keycloak ≥20 has this screen): 

   * **Client authentication:** **ON** (this makes it a confidential client)
   * **Authorization:** OFF (unless you want Keycloak’s fine-grained auth)
   * **Authentication flow:**

     * **Standard flow:** ON
     * **Direct access grants:** OFF (you don’t need password grant)
     * **Service accounts:** OFF  (not needed for browser login)
   * Click **Next**

4. Step 3 – *Login settings*:
   For **development**:

   * **Valid redirect URIs:**

     ```text
     http://localhost:5000/auth/callback
     ```
   * **Web origins:**

     ```text
     http://localhost:5000
     ```

   Optionally **Base URL**:
   `http://localhost:5000/`

   For **production**, add:

   * `https://flask-app.aiims.edu/auth/callback` to **Valid redirect URIs**
   * `https://flask-app.aiims.edu` to **Web origins** and maybe **Base URL**

   Click **Save**.

---

### C. Get the client secret for your Flask env

1. Still in **Realm: AIIMS_internal → Clients → flask-app**
2. Go to **Credentials** tab (or *‘Keys’ / ‘Credentials’* depending on Keycloak version).
3. Here you’ll see the **Client secret** once **Client authentication** is ON. ([Server Fault][3])
4. Copy it and set it in your Flask environment:

```bash
export KEYCLOAK_BASE_URL="https://sso.aiims.edu"
export KEYCLOAK_REALM="AIIMS_internal"
export KEYCLOAK_CLIENT_ID="flask-app"
export KEYCLOAK_CLIENT_SECRET="<paste-secret-here>"
export FLASK_SECRET_KEY="<strong-random-string>"
```

(or use a `.env` file / Docker secrets.)

---

### D. (Optional) Realm roles for RBAC

This matches the `role_required()` decorator in `app.py`.

1. In left menu: **Realm roles → Create role**

   * Create roles like:

     * `app_user`
     * `app_admin`
2. Assign to users:

   * **Users → click user → Role mappings**
   * In *Realm roles*, select `app_admin` or `app_user` → **Add selected**

These roles will appear in the token under `realm_access.roles`, and our Flask code reads them as:

```python
roles = userinfo.get("realm_access", {}).get("roles", [])
```

So `@role_required("app_admin")` will work.

(If you want to use the built-in `realm-admin` role instead, just assign that.)

---

## 2️⃣ kcadm CLI steps (scripted way)

Assuming you’re running `kcadm.sh` from the Keycloak container or locally.

### A. Login to Keycloak as admin

```bash
./kcadm.sh config credentials \
  --server https://sso.aiims.edu \
  --realm master \
  --user "<admin-username>" \
  --password "<admin-password>"
```

> This lets `kcadm` talk to Keycloak’s admin REST API. ([keycloak.org][1])

---

### B. Create the realm (if needed)

```bash
./kcadm.sh create realms \
  -s realm=AIIMS_internal \
  -s enabled=true
```

If realm already exists, this will fail; you can ignore that in your script or guard it with a check.

---

### C. Create the `flask-app` client

```bash
./kcadm.sh create clients -r AIIMS_internal \
  -s clientId=flask-app \
  -s protocol=openid-connect \
  -s enabled=true \
  -s publicClient=false \
  -s standardFlowEnabled=true \
  -s directAccessGrantsEnabled=false \
  -s serviceAccountsEnabled=false \
  -s 'redirectUris=["http://localhost:5000/auth/callback","https://flask-app.aiims.edu/auth/callback"]' \
  -s 'webOrigins=["http://localhost:5000","https://flask-app.aiims.edu"]'
```

Notes:

* `publicClient=false` → confidential client (requires secret)
* `standardFlowEnabled=true` → OIDC authorization code flow we use in Flask ([keycloak.org][4])

---

### D. Get the client UUID & secret

1. Get client ID (UUID):

```bash
CLIENT_UUID=$(
  ./kcadm.sh get clients -r AIIMS_internal -q clientId=flask-app \
  --fields id | jq -r '.[0].id'
)
echo "$CLIENT_UUID"
```

2. Get the secret:

```bash
./kcadm.sh get clients/$CLIENT_UUID/client-secret -r AIIMS_internal
```

The output will contain:

```json
{
  "type": "secret",
  "value": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

Use that `value` as `KEYCLOAK_CLIENT_SECRET` in your Flask env.

---

### E. Create realm roles and assign to user (via kcadm)

Create roles:

```bash
./kcadm.sh create roles -r AIIMS_internal -s name=app_user
./kcadm.sh create roles -r AIIMS_internal -s name=app_admin
```

Find target user:

```bash
./kcadm.sh get users -r AIIMS_internal -q username="vivek" --fields id,username
```

Suppose it returns an `id` like `1234-...-abcd`.

Assign `app_admin` to that user:

```bash
./kcadm.sh add-roles \
  -r AIIMS_internal \
  --uusername "vivek" \
  --rolename app_admin
```

Now `session["user"]["roles"]` in Flask will include `"app_admin"` after login, and:

```python
@role_required("app_admin")
def admin_panel():
    ...
```

will work.

---

## 3️⃣ Verify end-to-end

1. Start Flask app with the env vars set.
2. Open `http://localhost:5000/`
3. Click **Login with SSO** (from your Jinja template).
4. You should see the Keycloak login page for `AIIMS_internal`.
5. Login as a user that has `app_admin` (or whatever role you’re checking).
6. You should land on `/dashboard` and see:

   * name / email / username
   * roles list (including your realm roles)
7. Hit `/admin`:

   * If role present → page loads
   * If role missing → `403 Forbidden (missing role: app_admin)`

---

If you paste your **current realm name, base URL, and where Flask will live in prod** (path, domain), I can give you a ready-to-run kcadm bootstrap script that:

* creates realm (if missing)
* creates roles
* creates `flask-app` client
* prints out the client secret as an export command for your `.env`.

[1]: https://www.keycloak.org/docs/latest/server_admin/index.html?utm_source=chatgpt.com "Server Administration Guide"
[2]: https://developers.frontegg.com/agent-link/configuration/authentication/keycloak?utm_source=chatgpt.com "Keycloak"
[3]: https://serverfault.com/questions/1098895/how-to-get-the-client-id-and-client-secret-from-keycloak?utm_source=chatgpt.com "How to get the client-id and client-secret from keycloak?"
[4]: https://www.keycloak.org/securing-apps/oidc-layers?utm_source=chatgpt.com "Securing applications and services with OpenID Connect"
