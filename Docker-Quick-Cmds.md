
```bash

sudo docker compose up -d

sudo   docker exec -i auth_sso-keycloak-1 bash

# Copy out the default theme
sudo docker cp auth_sso-keycloak-1:/opt/keycloak/lib/lib/main/org.keycloak.keycloak-themes-26.4.4.jar ./default-keycloak-themes-26.4.4.jar
mkdir -p ./_base_themes && unzip default-keycloak-themes-26.4.4.jar -d ./_base_themes

```