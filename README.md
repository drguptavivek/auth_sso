# Keycloak SSO with Nginx Proxy Manager

This guide shows how to properly configure Keycloak to run behind Nginx Proxy Manager with TLS termination, avoiding mixed content issues and ensuring HTTPS URLs are generated correctly.

## Architecture Overview

```
Internet → HTTPS → Nginx Proxy Manager → HTTP → Keycloak (Port 8080)
```

- **External**: HTTPS termination at Nginx Proxy Manager
- **Internal**: HTTP communication between NPM and Keycloak
- **Result**: All URLs are HTTPS (no mixed content issues)

## 📁 File Structure

```
auth_sso/
├── .env                    # Keycloak configuration
├── docker-compose.yml     # Docker services
└── README.md              # This file

nginx-proxy-manager/
└── data/
    └── nginx/
        └── proxy_host/
            └── 3.conf    # NPM proxy host configuration
```

## 🔧 Configuration Files

### 1. Keycloak Environment Variables (.env)

```bash
# ===========================================
# Keycloak Reverse Proxy Configuration
# ===========================================
# IMPORTANT: Use HTTPS protocol in hostname for proper URL generation
KC_HOSTNAME=https://sso.aiims.edu

# HTTP configuration (required for TLS termination)
KC_HTTP_ENABLED=true

# Proxy headers configuration
KC_PROXY_HEADERS=forwarded
KC_PROXY_TRUSTED_ADDRESSES=127.0.0.1,172.16.0.0/12,192.168.0.0/16,172.24.0.1/24

# ===========================================
# Database Configuration
# ===========================================
KC_DB=postgres
KC_DB_URL=jdbc:postgresql://postgres:5432/keycloak
KC_DB_USERNAME=keycloak
KC_DB_PASSWORD=password

# ===========================================
# Admin Account
# ===========================================
KC_BOOTSTRAP_ADMIN_USERNAME=admin
KC_BOOTSTRAP_ADMIN_PASSWORD=gee8OhviIipu3OozXXXXXXXXXX

# ===========================================
# Health & Metrics
# ===========================================
KC_HEALTH_ENABLED=true
KC_METRICS_ENABLED=true
KC_HTTP_MANAGEMENT_PORT=9090

# ===========================================
# PostgreSQL Configuration
# ===========================================
POSTGRES_DB=keycloak
POSTGRES_USER=keycloak
POSTGRES_PASSWORD=password

# ===========================================
# Docker Images
# ===========================================
KEYCLOAK_IMAGE=quay.io/keycloak/keycloak:26.4.5
POSTGRES_IMAGE=postgres:17
```

### 2. Docker Compose Configuration (docker-compose.yml)

```yaml
services:
  keycloak:
    image: quay.io/keycloak/keycloak:26.4.5
    command: start
    mem_limit: 2g
    env_file:
      - .env
    ports:
      - "8080:8080"  # Internal HTTP port (not exposed publicly)
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - web
      - db_net
    restart: unless-stopped

  postgres:
    image: postgres:17
    mem_limit: 2g
    env_file:
      - .env
    volumes:
      - postgres_data:/var/lib/postgresql/17/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-keycloak}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - db_net
    restart: unless-stopped

volumes:
  postgres_data:

networks:
  web:
    external: true
  db_net:
    external: true
```

### 3. Nginx Proxy Manager Configuration

**Location**: `../nginx-proxy-manager/data/nginx/proxy_host/3.conf`

```nginx
# ------------------------------------------------------------
# sso.aiims.edu - Keycloak Proxy Configuration
# ------------------------------------------------------------

map $scheme $hsts_header {
    https   "max-age=63072000; preload";
}

server {
  set $forward_scheme http;          # Internal: HTTP to Keycloak
  set $server         "host.docker.internal";
  set $port           8080;           # Keycloak internal port

  listen 80;
  listen 443 ssl;

  server_name sso.aiims.edu;
  http2 on;

  # SSL Configuration (managed by NPM)
  ssl_certificate /data/custom_ssl/npm-1/fullchain.pem;
  ssl_certificate_key /data/custom_ssl/npm-1/privkey.pem;

  # Force SSL redirect
  include conf.d/include/force-ssl.conf;

  access_log /data/logs/proxy-host-3_access.log proxy;
  error_log /data/logs/proxy-host-3_error.log warn;

  # Keycloak-specific proxy headers
  proxy_set_header X-Forwarded-Host $host;
  proxy_set_header X-Forwarded-Proto $scheme;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header Host $host;

  # Handle redirects from HTTP to HTTPS
  proxy_redirect http://$host https://$host;
  proxy_redirect http://$proxy_host https://$host;

  # WebSocket support for Keycloak
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";

  location / {
    # Include standard proxy configuration
    include conf.d/include/proxy.conf;
  }

  # Custom configurations
  include /data/nginx/custom/server_proxy[.]conf;
}
```

## 🚀 Deployment Steps

### 1. Update DNS and SSL

1. **DNS**: Point `sso.aiims.edu` to your Nginx Proxy Manager server
2. **SSL**: Install SSL certificate in Nginx Proxy Manager dashboard
3. **Proxy Host**: Create proxy host in NPM dashboard:
   - **Domain**: `sso.aiims.edu`
   - **Scheme**: `https`
   - **Forward Hostname/IP**: `host.docker.internal`
   - **Forward Port**: `8080`
   - **Block Common Exploits**: ✅ enabled

### 2. Deploy Keycloak

```bash
# Navigate to auth_sso directory
cd /Users/vivekgupta/workspace/auth_sso

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f keycloak

# Wait for startup (usually 30-60 seconds)
```

### 3. Verify Configuration

```bash
# Test direct connection to Keycloak
curl -I http://localhost:8080

# Test through proxy
curl -k -I https://sso.aiims.edu/

# Test admin console
curl -k -I https://sso.aiims.edu/admin/
```

### 4. Access Keycloak Admin Console

1. **URL**: `https://sso.aiims.edu/admin/`
2. **Username**: `admin`
3. **Password**: Check `.env` file for `KC_BOOTSTRAP_ADMIN_PASSWORD`

## 🔍 Troubleshooting

### Common Issues & Solutions

#### 1. Mixed Content Errors
**Problem**: Browser console shows "Mixed Content" warnings
**Solution**: Ensure `KC_HOSTNAME=https://sso.aiims.edu` (with https:// protocol)

#### 2. 502 Bad Gateway Errors
**Problem**: NPM shows 502 errors
**Solutions**:
- Verify Keycloak is running: `docker-compose ps keycloak`
- Check hostname resolution: `docker exec nginx-proxy-manager-app-1 getent hosts host.docker.internal`
- Ensure port 8080 is accessible from NPM container

#### 3. HTTP URLs in HTTPS Pages
**Problem**: Keycloak generates HTTP URLs instead of HTTPS
**Solution**:
- Use `KC_HOSTNAME=https://sso.aiims.edu` (include protocol)
- Set `KC_HTTP_ENABLED=true` for TLS termination
- Remove `KC_HTTPS_ENABLED=true` (conflicts with TLS termination)

#### 4. Proxy Headers Not Working
**Problem**: Keycloak doesn't recognize proxy headers
**Solutions**:
- Ensure `KC_PROXY_HEADERS=forwarded`
- Add your proxy IPs to `KC_PROXY_TRUSTED_ADDRESSES`
- Check NPM proxy headers configuration

### Debug Commands

```bash
# Check Keycloak environment
docker exec auth_sso-keycloak-1 env | grep KC_

# Check Keycloak logs
docker logs auth_sso-keycloak-1 --tail 50

# Test proxy headers
docker exec nginx-proxy-manager-app-1 nginx -T | grep -A5 -B5 proxy_set_header

# Check access logs
tail -f ../nginx-proxy-manager/data/logs/proxy-host-3_access.log

# Check error logs
tail -f ../nginx-proxy-manager/data/logs/proxy-host-3_error.log
```

## 📋 Configuration Checklist

- [ ] DNS points to Nginx Proxy Manager
- [ ] SSL certificate installed in NPM
- [ ] `.env` has `KC_HOSTNAME=https://sso.aiims.edu`
- [ ] `.env` has `KC_HTTP_ENABLED=true`
- [ ] `.env` does NOT have `KC_HTTPS_ENABLED=true`
- [ ] `KC_PROXY_HEADERS=forwarded` is set
- [ ] Proxy IPs are in `KC_PROXY_TRUSTED_ADDRESSES`
- [ ] NPM proxy host configured correctly
- [ ] Keycloak containers are running
- [ ] Admin console accessible via HTTPS
- [ ] No mixed content errors in browser console

## 🔄 Maintenance

### Regular Updates

```bash
# Update images
docker-compose pull

# Restart with new images
docker-compose down
docker-compose up -d --build

# Clear cache if needed
docker-compose down
docker system prune -f
docker-compose up -d
```

### Backup Configuration

```bash
# Backup environment file
cp .env .env.backup.$(date +%Y%m%d)

# Backup database
docker exec auth_sso-postgres-1 pg_dump -U keycloak keycloak > keycloak_backup_$(date +%Y%m%d).sql
```

## 📚 Additional Resources

- [Keycloak Reverse Proxy Documentation](https://www.keycloak.org/server/reverseproxy)
- [Keycloak Server Configuration](https://www.keycloak.org/server/configuration)
- [Nginx Proxy Manager Documentation](https://nginx-proxy-manager.com/)

---

**⚠️ Important Notes**:

1. **Security**: Never expose Keycloak port 8080 directly to the internet
2. **TLS Termination**: Always terminate SSL at the reverse proxy, not at Keycloak
3. **Headers**: Ensure proxy headers are properly configured and trusted
4. **Updates**: Regularly update Keycloak and PostgreSQL images for security patches