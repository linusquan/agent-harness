# Add webhook_url Docker Secret for nodejs Service on srv3

## Summary

Added a new Docker secret called `webhook_url` for the `nodejs` service on srv3 (test server). This was a dry-run simulation -- no SSH commands were executed against the server.

## Commands That Would Be Run on srv3

```bash
# 1. Create the Docker secret on the swarm
ssh srv3 'echo -n "<WEBHOOK_URL_VALUE>" | docker secret create webhook_url -'

# 2. Redeploy the stack to pick up the new secret
ssh srv3 'cd ~/docker-server/main-v2 && docker stack deploy -c ~/docker-server/deploy-test/docker-stack.yml scgc'

# 3. Verify the secret exists
ssh srv3 'docker secret ls'

# 4. Verify the nodejs service restarted and is healthy
ssh srv3 'docker service ps scgc_nodejs --no-trunc'
```

## Documentation Updated

### 1. `src/docker-stack.yml`
- Added `webhook_url` to the `nodejs` service's `secrets:` list
- Added `WEBHOOK_URL_FILE=/run/secrets/webhook_url` environment variable to the `nodejs` service
- Added `webhook_url` to the top-level `secrets:` section as `external: true`

### 2. `src/infra-doc/secrets-inventory.md`
- Added row: `webhook_url` | `nodejs` | Webhook endpoint URL

### 3. `src/infra-doc/changelog.md`
- Added entry under 2026-04-14 documenting the new secret addition

## Notes

- The actual secret value must be provided at creation time on the server -- it is never stored in the repository.
- After creating the secret on the server, the updated `docker-stack.yml` must be deployed (either via CI pushing to `deploy-test` branch, or manually with `docker stack deploy`).
- The nodejs application code must read the secret from `/run/secrets/webhook_url` (or via the `WEBHOOK_URL_FILE` environment variable pattern already used by the service).
