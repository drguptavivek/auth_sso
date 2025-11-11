Always use 127.0.0.1 in port mapping. Else Keycloak will deny login from non-private client IPs

See # https://github.com/quarkusio/quarkus/discussions/48905

Another  only solution that worked  is to switch the Docker Desktop on Mac setting > General > Virtual Machine Options from Apple Virtualization framework to Docker VMM (which is faster anyway), then I no longer got HTTPS required. In my case, I couldn't add the host 127.0.0.1 to the Docker port binding.


See # https://github.com/keycloak/keycloak/issues/30112#issuecomment-3057078825




# Behind a revre proxy
- By default, Keycloak mandates the configuration of the hostname option and does not dynamically resolve URLs.




Keycloak runs on the following ports by default:
 - 8443 (8080 when you enable HTTP explicitly by --http-enabled=true)
 - 9000
The port 8443 (or 8080 if HTTP is enabled) is used for the Admin UI, Account Console, SAML and OIDC endpoints and the Admin REST API as described in the Configuring the hostname (v2) guide.
The port 9000 is used for management, which includes endpoints for health checks and metrics as described in the Configuring the Management Interface guide.




bin/kc.[sh|bat] start --hostname https://my.keycloak.org --proxy-headers xforwarded


# Exposing the Administration Console on a separate hostname
bin/kc.[sh|bat] start --hostname https://my.keycloak.org --hostname-admin https://admin.my.keycloak.org:8443
 - Using the hostname-admin option does not prevent accessing the Administration REST API endpoints via the frontend URL specified by the hostname option. If you want to restrict access to the Administration REST API, you need to do it on the reverse proxy level. Administration Console implicitly accesses the API using the URL as specified by the hostname-admin option. 


##  To troubleshoot the hostname configuration, use a  debug tool:
bin/kc.[sh|bat] start --hostname=mykeycloak --hostname-debug=true
- After Keycloak starts properly, open your browser and go to: http://mykeycloak:8080/realms/<your-realm>/hostname-debug



