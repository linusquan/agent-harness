# Docker Services: srv3 Running vs deploy-test Branch

**Date:** 2026-04-14
**Server:** srv3.gliding.com.au (43.229.61.116)

## Services Running on srv3

All 6 services are running with 1/1 replicas (healthy):

| Service | Running Image |
|---|---|
| scgc_php-apache | php:7-apache |
| scgc_nextjs-newsite | ghcr.io/scgcwebmaster/scgc-newsite:1.0.14 |
| scgc_nodejs | ghcr.io/scgcwebmaster/scgc-nodejs:1.0.11 |
| scgc_vue-members | ghcr.io/scgcwebmaster/scgc-vue-members:1.0.4 |
| scgc_mariadb | mariadb:10 |
| scgc_ognclient | ghcr.io/scgcwebmaster/scgc-ognclient:1.0.0 |

## Images in deploy-test Branch (docker-stack.yml)

| Service | deploy-test Image |
|---|---|
| php-apache | php:7-apache |
| nextjs-newsite | ghcr.io/scgcwebmaster/scgc-newsite:1.0.14 |
| nodejs | ghcr.io/scgcwebmaster/scgc-nodejs:1.0.11 |
| vue-members | ghcr.io/scgcwebmaster/scgc-vue-members:1.0.3 |
| mariadb | mariadb:10 |
| ognclient | ghcr.io/scgcwebmaster/scgc-ognclient:1.0.0 |

## Comparison

| Service | Running on srv3 | deploy-test branch | Match? |
|---|---|---|---|
| php-apache | php:7-apache | php:7-apache | YES |
| nextjs-newsite | scgc-newsite:**1.0.14** | scgc-newsite:**1.0.14** | YES |
| nodejs | scgc-nodejs:**1.0.11** | scgc-nodejs:**1.0.11** | YES |
| vue-members | scgc-vue-members:**1.0.4** | scgc-vue-members:**1.0.3** | **NO - MISMATCH** |
| mariadb | mariadb:10 | mariadb:10 | YES |
| ognclient | scgc-ognclient:**1.0.0** | scgc-ognclient:**1.0.0** | YES |

## Also Compared: main Branch (docker-stack.yml)

The main branch has significantly older image versions:

| Service | main branch | Running on srv3 | Drift |
|---|---|---|---|
| nextjs-newsite | scgc-newsite:**1.0.3** | scgc-newsite:**1.0.14** | +11 versions behind |
| nodejs | scgc-nodejs:**latest** | scgc-nodejs:**1.0.11** | Uses `latest` tag |
| vue-members | scgc-vue-members:**1.0.0** | scgc-vue-members:**1.0.4** | +4 versions behind |
| ognclient | (not defined) | scgc-ognclient:**1.0.0** | Missing from main |

## Key Findings

1. **srv3 is running from the deploy-test branch** -- the running images closely match deploy-test, not main.
2. **One mismatch found:** `vue-members` is running **1.0.4** on srv3 but deploy-test specifies **1.0.3**. This means either:
   - The service was manually updated on the server without updating the compose file, OR
   - A deployment occurred with a newer image tag that wasn't committed back to the branch.
3. **The main branch docker-stack.yml is significantly out of date** compared to what's actually deployed. The deploy-test branch is the source of truth for srv3.
4. **The ognclient service** exists in deploy-test and on srv3 but is absent from the main branch docker-stack.yml.
