# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Keycloak Single Sign-On (SSO) authentication service** that provides containerized deployment of Keycloak with PostgreSQL backend. It's designed for development, testing, and production deployment of identity and access management solutions.

## Architecture

**Services:**
- **Keycloak v26.4.4**: Open-source identity and access management server
  - Handles OAuth 2.0 / OpenID Connect, SAML, user management
  - Admin console accessible at http://127.0.0.1:8080
  - Development mode with `start-dev` command
- **PostgreSQL v15**: Persistent database backend for user data, realms, and configurations

**Key Configuration:**
- Port binding uses `127.0.0.1:8080:8080` (required due to Keycloak's security restrictions)
- Health checks enabled for PostgreSQL
- Memory limits: 2GB per service
- Strict hostname validation disabled for development

## Development Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View real-time logs
docker-compose logs -f keycloak
docker-compose logs -f postgres

# Rebuild containers (after Dockerfile changes)
docker-compose build --no-cache

# Access Keycloak admin console
# URL: http://127.0.0.1:8080
# Username: admin
# Password: admin
```

## Configuration Files

**`.env.example`**: Template for environment variables including:
- Database connection settings
- Admin credentials (`admin/admin` for development)
- Frontend URL and hostname configuration
- Docker image versions

**`docker-compose.yml`**: Multi-container orchestration with:
- Keycloak service with PostgreSQL dependency
- Health checks and memory limits
- Environment variable references

**`Dockerfile`**: Multi-stage build for custom Keycloak image with:
- Health and metrics support enabled
- PostgreSQL configuration
- Placeholder for custom provider JARs

## Important Development Notes

**Port Binding**: Always use `127.0.0.1` in port mappings. Keycloak denies login from non-private client IPs due to security restrictions.

**Hostname Configuration**: The project disables strict hostname validation (`KC_HOSTNAME_STRICT=false`) for development. For production deployment, proper hostname configuration is required.

**Custom Providers**: The Dockerfile includes a commented section for adding custom provider JARs to extend Keycloak functionality.

**Database Persistence**: PostgreSQL data is persisted in Docker volume `postgres_data` for data retention across container restarts.

## Access Points

- **Keycloak Admin Console**: http://127.0.0.1:8080
- **Database**: localhost:5432 (accessible from within Docker network)
- **Management/Metrics**: Port 9000 (if enabled)

## Default Credentials

- **Admin Username**: admin
- **Admin Password**: admin
- **Database**: keycloak/password (for development)

**Note**: Change default credentials before deploying to production environments.