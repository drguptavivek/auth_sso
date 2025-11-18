#!/usr/bin/env bash
set -euo pipefail

# ---------------- Env loading ----------------
# Default env file names; override via ENV_FILE / REALM_ENV_FILE if needed
ENV_FILE="${ENV_FILE:-.env}"
REALM_ENV_FILE="${REALM_ENV_FILE:-.env.realm}"

if [ -f "$ENV_FILE" ]; then
  echo "Loading base env from $ENV_FILE"
  set -o allexport
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +o allexport
else
  echo "WARN: $ENV_FILE not found – continuing without it"
fi

if [ -f "$REALM_ENV_FILE" ]; then
  echo "Loading realm env from $REALM_ENV_FILE"
  set -o allexport
  # shellcheck disable=SC1090
  source "$REALM_ENV_FILE"
  set +o allexport
else
  echo "WARN: $REALM_ENV_FILE not found – continuing without it"
fi

# ---------------- Config from env ----------------
# Container running Keycloak
KC_CONTAINER="${KC_CONTAINER:-keycloak}"

# Internal URL for kcadm from inside the container.
# For Keycloak 17+ the base path has no /auth.
KC_INTERNAL_URL="${KC_INTERNAL_URL:-http://localhost:8080}"

# Master (bootstrap) admin credentials from .env
MASTER_USER="${KC_BOOTSTRAP_ADMIN_USERNAME:?KC_BOOTSTRAP_ADMIN_USERNAME is not set}"
MASTER_PASS="${KC_BOOTSTRAP_ADMIN_PASSWORD:?KC_BOOTSTRAP_ADMIN_PASSWORD is not set}"

# Realm + realm admin from .env.realm
REALM_NAME="${REALM_NAME:-AIIMS_INTERNAL}"
REALM_ADMIN_USER="${REALM_ADMIN_USER:-realm-admin}"
REALM_ADMIN_PASS="${REALM_ADMIN_PASS:?REALM_ADMIN_PASS is not set}"

echo "== Keycloak realm bootstrap =="
echo "Container      : $KC_CONTAINER"
echo "Server URL     : $KC_INTERNAL_URL"
echo "Master admin   : $MASTER_USER"
echo "Target realm   : $REALM_NAME"
echo "Realm admin    : $REALM_ADMIN_USER"
echo

# kcadm inside container
KCADM=(docker exec "$KC_CONTAINER" /opt/keycloak/bin/kcadm.sh)

# ---------------- 1) Login to master realm ----------------
echo "[1/4] Login to master realm via kcadm"
"${KCADM[@]}" config credentials \
  --server "$KC_INTERNAL_URL" \
  --realm master \
  --user "$MASTER_USER" \
  --password "$MASTER_PASS"

# ---------------- 2) Ensure realm exists ----------------
echo "[2/4] Ensure realm '$REALM_NAME' exists"
if ! "${KCADM[@]}" get "realms/$REALM_NAME" >/dev/null 2>&1; then
  "${KCADM[@]}" create realms \
    -s realm="$REALM_NAME" \
    -s enabled=true
  echo "  → Created realm '$REALM_NAME'"
else
  echo "  → Realm '$REALM_NAME' already exists, skipping create"
fi

# ---------------- 3) Ensure realm admin user exists ----------------
echo "[3/4] Ensure realm admin user '$REALM_ADMIN_USER' exists"

# Extra: account info (optional but recommended)
REALM_ADMIN_EMAIL="${REALM_ADMIN_EMAIL:-}"
REALM_ADMIN_FIRST_NAME="${REALM_ADMIN_FIRST_NAME:-}"
REALM_ADMIN_LAST_NAME="${REALM_ADMIN_LAST_NAME:-}"

USER_ID=$("${KCADM[@]}" get users -r "$REALM_NAME" \
  -q username="$REALM_ADMIN_USER" \
  --fields id \
  --format csv \
  --noquotes 2>/dev/null | head -n1 | tr -d '\r')

if [ -z "${USER_ID:-}" ]; then
  echo "  → User not found, creating..."
  CREATED_OUTPUT=$("${KCADM[@]}" create users -r "$REALM_NAME" \
    -s username="$REALM_ADMIN_USER" \
    -s enabled=true \
    -s email="${REALM_ADMIN_EMAIL}" \
    -s firstName="${REALM_ADMIN_FIRST_NAME}" \
    -s lastName="${REALM_ADMIN_LAST_NAME}" \
    -s emailVerified=true 2>&1)

  echo "$CREATED_OUTPUT"

  USER_ID=$("${KCADM[@]}" get users -r "$REALM_NAME" \
    -q username="$REALM_ADMIN_USER" \
    --fields id \
    --format csv \
    --noquotes 2>/dev/null | head -n1 | tr -d '\r')

  if [ -z "${USER_ID:-}" ]; then
    echo "ERROR: Could not resolve user ID for '$REALM_ADMIN_USER' after creation" >&2
    exit 1
  fi

  echo "  → Created user '$REALM_ADMIN_USER' (id=$USER_ID)"
else
  echo "  → User '$REALM_ADMIN_USER' already exists (id=$USER_ID)"

  # Update account information in case it's missing/changed
  echo "  → Updating account info (email, first name, last name)"
  "${KCADM[@]}" update "users/$USER_ID" -r "$REALM_NAME" \
    -s email="${REALM_ADMIN_EMAIL}" \
    -s firstName="${REALM_ADMIN_FIRST_NAME}" \
    -s lastName="${REALM_ADMIN_LAST_NAME}" \
    -s emailVerified=true >/dev/null
fi

# ---------------- 4) Set password + grant realm-admin ----------------
echo "[4/4] Set password and grant realm-admin role"

# Always set/reset password via user ID
"${KCADM[@]}" set-password -r "$REALM_NAME" \
  --userid "$USER_ID" \
  --new-password "$REALM_ADMIN_PASS" \
  --temporary=false

# Find the realm-management client ID
CLIENT_ID=$("${KCADM[@]}" get clients -r "$REALM_NAME" \
  -q clientId=realm-management \
  --fields id \
  --format csv \
  --noquotes 2>/dev/null | head -n1 | tr -d '\r')

if [ -z "${CLIENT_ID:-}" ]; then
  echo "WARN: Could not find 'realm-management' client in realm '$REALM_NAME'; skipping role grant" >&2
else
  # Grant realm-admin client role using user ID + client ID
  "${KCADM[@]}" add-roles -r "$REALM_NAME" \
    --uid "$USER_ID" \
    --cid "$CLIENT_ID" \
    --rolename realm-admin || {
      echo "WARN: add-roles failed – check if 'realm-admin' role exists on client 'realm-management'" >&2
    }
fi

echo

# Build public base URL: prefer KC_HOSTNAME if set, else fall back to internal URL
PUBLIC_BASE="${KC_HOSTNAME:-$KC_INTERNAL_URL}"
PUBLIC_BASE="${PUBLIC_BASE%/}"  # strip trailing slash if any

echo "Done."
echo "You can now log in to realm '$REALM_NAME' as '$REALM_ADMIN_USER'."
echo "Admin console URL: $PUBLIC_BASE/admin/$REALM_NAME/console"
