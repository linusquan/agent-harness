# Add Docker Secret: webhook_url for nodejs service on srv3

## Dry-Run Summary

This document describes the exact steps to add a new Docker secret called `webhook_url` for the `nodejs` service on srv3 (test server at 43.229.61.116).

## Step 1: Create the Docker secret on srv3

SSH into the test server and create the secret:

```bash
ssh srv3
echo -n "<WEBHOOK_URL_VALUE>" | docker secret create webhook_url -
```

Verify it was created:

```bash
docker secret ls
docker secret inspect webhook_url
```

## Step 2: Update docker-stack.yml

File: `src/docker-stack.yml`

### 2a. Add environment variable to the nodejs service

In the `nodejs` service `environment` section, add:

```yaml
      - WEBHOOK_URL_FILE=/run/secrets/webhook_url
```

(After the existing `NAIPS_PASSWORD_FILE` line, at line 175.)

### 2b. Add secret reference to the nodejs service

In the `nodejs` service `secrets` section, add:

```yaml
      - webhook_url
```

(After the existing `naips_password` entry, at line 187.)

### 2c. Declare the secret at the top-level secrets block

In the top-level `secrets:` section, add:

```yaml
  webhook_url:
    external: true
```

(After the existing `naips_password` entry, at line 298.)

## Step 3: Redeploy the stack

```bash
ssh srv3
cd /path/to/stack
docker stack deploy -c docker-stack.yml scgc
```

## Step 4: Update documentation

The following files need to be updated to include the new secret:

### 4a. `.artifacts/infra/vps-docker-secrets.md`

Add a row to the "Secrets Required for nodejs Service" table:

| Secret name | Description | Where to find current value |
|---|---|---|
| `webhook_url` | Webhook callback URL | (source TBD) |

Add to the "Creation Commands" section:

```bash
# Webhook
echo -n "<VALUE>" | docker secret create webhook_url -
```

### 4b. `src/infra-doc/secrets-inventory.md`

Add a row to the srv3 table:

| `webhook_url` | nodejs | Webhook callback URL |

### 4c. `.artifacts/infra/create-secrets-test-prod.sh`

Add to the script:

```bash
# Webhook
create_secret webhook_url             "<VALUE>"
```

### 4d. `src/secrets/create-secrets.sh`

Add to the script:

```bash
# Webhook
create_secret webhook_url             ""
```

## Step 5: Verify in the running container

```bash
docker exec $(docker ps -q -f name=scgc_nodejs) ls -la /run/secrets/webhook_url
docker exec $(docker ps -q -f name=scgc_nodejs) cat /run/secrets/webhook_url
```

## Files Modified

| File | Change |
|------|--------|
| `src/docker-stack.yml` | Add env var, service secret ref, and top-level secret declaration |
| `.artifacts/infra/vps-docker-secrets.md` | Document the new secret |
| `src/infra-doc/secrets-inventory.md` | Add webhook_url to inventory table |
| `.artifacts/infra/create-secrets-test-prod.sh` | Add create_secret line |
| `src/secrets/create-secrets.sh` | Add create_secret line (empty placeholder) |

## Application Code Note

The nodejs application must be updated to read the secret from the file path. The standard pattern used in this stack is to read secrets via `_FILE` environment variables, e.g.:

```javascript
const webhookUrl = fs.readFileSync(process.env.WEBHOOK_URL_FILE, 'utf8').trim();
```
