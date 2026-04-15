# srv3 Docker Services Check — 2026-04-14

## Running Services on srv3

| Service | Running Image | Replicas | Status |
|---------|--------------|----------|--------|
| scgc_mariadb | mariadb:10 | 1/1 | Running |
| scgc_nextjs-newsite | ghcr.io/scgcwebmaster/scgc-newsite:1.0.14 | 1/1 | Running |
| scgc_nodejs | ghcr.io/scgcwebmaster/scgc-nodejs:1.0.11 | 1/1 | Running |
| scgc_ognclient | ghcr.io/scgcwebmaster/scgc-ognclient:1.0.0 | 1/1 | Running |
| scgc_php-apache | php:7-apache | 1/1 | Running |
| scgc_vue-members | ghcr.io/scgcwebmaster/scgc-vue-members:1.0.4 | 1/1 | Running |

## deploy-test Branch Image Versions (docker-stack.yml)

| Service | Image in deploy-test |
|---------|---------------------|
| php-apache | php:7-apache |
| nextjs-newsite | ghcr.io/scgcwebmaster/scgc-newsite:1.0.14 |
| nodejs | ghcr.io/scgcwebmaster/scgc-nodejs:1.0.11 |
| ognclient | ghcr.io/scgcwebmaster/scgc-ognclient:1.0.0 |
| vue-members | ghcr.io/scgcwebmaster/scgc-vue-members:1.0.4 |
| mariadb | mariadb:10 |

## Comparison Result

| Service | Running Version | deploy-test Version | Match? |
|---------|----------------|--------------------|---------|
| php-apache | php:7-apache | php:7-apache | YES |
| nextjs-newsite | scgc-newsite:1.0.14 | scgc-newsite:1.0.14 | YES |
| nodejs | scgc-nodejs:1.0.11 | scgc-nodejs:1.0.11 | YES |
| ognclient | scgc-ognclient:1.0.0 | scgc-ognclient:1.0.0 | YES |
| vue-members | scgc-vue-members:1.0.4 | scgc-vue-members:1.0.4 | YES |
| mariadb | mariadb:10 | mariadb:10 | YES |

## Summary

All 6 services on srv3 are running and healthy (1/1 replicas each). Every running image version exactly matches what is specified in the deploy-test branch's `docker-stack.yml`. There are no version mismatches — the server is fully in sync with the deploy-test configuration.
