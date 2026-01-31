---
name: scgc-document-publish
description: Upload a document (PDF, image, etc.) to the SCGC club website by adding it to scgc-data, updating pug templates in my-gliding-club, creating a GitHub PR, and deploying via SSH service update
---

# Add documents

## Instructions

You are responsible for adding a document and make it available in the club website.

The website repository is under `scgc-monorepo`. everything you need to operate is under this directory

Most of your workflow is receiving a file and then update the content under `scgc-monorepo/scgc-data` by asking questions of where it should be placed if you can not decide based on the file content.

The `my-gliding-club` folder contains the code in static nodejs .pug file referencing the file under scgc-data, make appropriate code change and let human review, push code to git repository.

## Examples

- Received a file named commitee_minutes_2025_07.pdf
- add the file under `scgc-data/private/committee-minutes`.
- found the `my-gliding-club/app/views/minutes.pug` create a new li with file name.
- branch from the current git `branch`, create a pull request with `docs-update/<date-content>` format github cli push code, raise a pull request.
