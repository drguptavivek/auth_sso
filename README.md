# Keycloak SSO Setup with PostgreSQL

This repository contains a Docker Compose configuration for running Keycloak with PostgreSQL for Single Sign-On (SSO) authentication. The setup includes both development and production configurations with optimized settings.

## Features

- Development and Production environments
- PostgreSQL database integration
- Optimized cache configuration
- Health monitoring and metrics
- Memory optimization
- Security hardening
- Docker Compose override support

## Prerequisites

- Docker
- Docker Compose v2
- Git
- 4GB RAM minimum (8GB recommended for production)

## Quick Start

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd auth_sso
   ```

2. Development Setup:
   ```bash
   # Copy development configuration
   cp docker-compose.override.yml.example docker-compose.override.yml
   
   # Start Keycloak in development mode
   docker-compose up
   ```

3. Production Setup:
   ```bash
   # Copy and edit production environment file
   cp prod.env.example prod.env
   
   # Start with production configuration
   docker-compose -f docker-compose.yml --env-file prod.env up -d
   ```

4. Access Keycloak:
   - Development: http://localhost:8080
   - Production: https://your-domain:8443
   - Admin Console: /admin
   - Default credentials:
     - Username: admin
     - Password: admin (change immediately)

## Environment Configurations

### Development Mode

```bash
# Using docker-compose.override.yml
docker-compose up
```

Features:
- HTTP enabled for local development
- Local caching
- Debug-friendly settings
- Exposed ports for easy access
- Lower resource limits
- Hot-reload enabled
- Development-specific memory settings

### Production Mode

```bash
# Using production settings
docker-compose -f docker-compose.yml --env-file prod.env up -d
```

Features:
- HTTPS enforced
- Optimized caching
- Enhanced security
- Health monitoring
- Performance tuning
- Resource management
- Production-grade memory settings

## Advanced Configuration

### Cache Optimization

Development:
```yaml
KC_CACHE: local
KC_CACHE_STACK: ""
```

Production:
```yaml
KC_CACHE: enabled
KC_CACHE_STACK: kubernetes
KC_CACHE_EMBEDDED_MTLS_ENABLED: true
KC_CACHE_EMBEDDED_USERS_MAX_COUNT: 50000
KC_CACHE_EMBEDDED_SESSIONS_MAX_COUNT: 25000
KC_CACHE_METRICS_HISTOGRAMS_ENABLED: true
```

### Memory Management

Development:
```yaml
JAVA_OPTS: -Xms256m -Xmx1024m
```

Production:
```yaml
JAVA_OPTS: -XX:MaxRAMPercentage=70 -XX:InitialRAMPercentage=50 -XX:MaxHeapFreeRatio=30
KC_MEMORY_LIMIT: 4G
KC_MEMORY_RESERVATION: 2G
```

### Performance Tuning

```yaml
KC_HTTP_MAX_QUEUED_REQUESTS: 1000
KC_HTTP_POOL_MAX_THREADS: 100
KC_TRANSACTION_XA_ENABLED: false
```

### Health Monitoring

Endpoints:
- Readiness: /health/ready
- Liveness: /health/live
- Metrics: /metrics (when enabled)

Configuration:
```yaml
KC_HEALTH_ENABLED: true
KC_METRICS_ENABLED: true
KC_HTTP_METRICS_HISTOGRAMS_ENABLED: true
```

## Security Best Practices

1. SSL/TLS Configuration:
   - Use proper certificates in production
   - Enable strict HTTPS
   - Configure proper key stores

2. Authentication:
   - Change default admin password
   - Use strong passwords
   - Enable 2FA for admin console

3. Network Security:
   - Use proper firewalls
   - Configure rate limiting
   - Enable brute force protection

4. Monitoring:
   - Enable audit logging
   - Monitor metrics
   - Set up alerts

## Maintenance

### Backup

1. Database:
   ```bash
   docker-compose exec postgres pg_dump -U keycloak keycloak > backup.sql
   ```

2. Realm Configuration:
   ```bash
   docker-compose exec keycloak /opt/keycloak/bin/kc.sh export --file /tmp/realm-export.json
   ```

### Scaling

Horizontal scaling in production:
1. Configure load balancer
2. Enable distributed caching
3. Setup session affinity
4. Use proper database scaling

### Monitoring

1. Health Status:
   ```bash
   curl https://your-domain:8443/health
   ```

2. Metrics:
   ```bash
   curl https://your-domain:8443/metrics
   ```

3. Logs:
   ```bash
   docker-compose logs -f keycloak
   docker-compose logs -f postgres
   ```

## Troubleshooting

1. Memory Issues:
   - Check memory usage: `docker stats`
   - Verify JVM settings
   - Monitor GC logs

2. Connection Issues:
   - Verify network settings
   - Check SSL configuration
   - Validate database connection

3. Performance Problems:
   - Monitor cache statistics
   - Check thread pool usage
   - Analyze database queries

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow coding standards
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]