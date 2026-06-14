# GitLab CE CI/CD Pipeline

This document explains every part of `.gitlab-ci.yml`.

---

## Overview

```
Tag push (v*)  ──►  build  ──►  publish  ──►  retag
Branch push    ──►  build  (no push)
```

The pipeline has **three stages**:

| Stage | Jobs | Trigger |
|---|---|---|
| `build` | `build:bot`, `build:web` | All branches + tag pushes |
| `publish` | `publish:bot`, `publish:web` | Tag pushes (`v*`) only |
| `retag` | `retag:cleanup-old-latest` | Tag pushes (`v*`) only |

---

## How to Trigger a Release

1. Commit and push your changes to the default branch.
2. Create and push a tag following **semantic versioning** with a `v` prefix:

```bash
git tag v1.2.3
git push origin v1.2.3
```

The pipeline will automatically:
1. Build both Docker images (`bot` and `web`).
2. Tag them with `v1.2.3` and push to the GitLab Container Registry.
3. Tag them with `latest` and push.
4. Remove old ephemeral `build-*` tags from the registry.

---

## Stage Details

### `build` stage

**Jobs:** `build:bot`, `build:web`

```yaml
image: docker:27
services:
  - docker:27-dind
```

- Uses Docker-in-Docker (`dind`) to build images inside CI.
- Pulls the previous `latest` image for **layer caching** (`--cache-from`).
  This dramatically speeds up builds — unchanged layers are reused.
- Tags the built image as `bot:build-<pipeline_iid>` and pushes it to the registry.
  This ephemeral tag is used by the next stage.

**Runs on:** Every push to the default branch and every tag push.  
This ensures images always build successfully before a release.

---

### `publish` stage

**Jobs:** `publish:bot`, `publish:web`

```yaml
needs: [build:bot]   # waits for the build job, skips if build fails
rules:
  - if: '$CI_COMMIT_TAG =~ /^v/'
```

- Pulls the ephemeral `build-<pipeline_iid>` image from the previous stage.
- Re-tags it with **the Git tag** (e.g. `v1.2.3`) and pushes.
- Re-tags it with **`latest`** and pushes — this updates `latest` to the new release.

**Runs on:** Tag pushes matching `v*` only.

---

### `retag` stage

**Job:** `retag:cleanup-old-latest`

```yaml
needs: [publish:bot, publish:web]
```

- Uses the **GitLab Container Registry REST API** to find all tags in the `bot` and `web` repositories.
- Deletes all `build-*` ephemeral tags that were created in the build stage.
- Does **not** touch the `latest` or the version tag — those are kept forever.

This keeps the registry clean by removing intermediate build tags automatically.

---

## Variables

### Built-in GitLab Variables (automatically available)

| Variable | Value |
|---|---|
| `CI_REGISTRY` | Your GitLab instance's registry hostname |
| `CI_REGISTRY_IMAGE` | The project's registry image path, e.g. `registry.gitlab.example.com/group/repo` |
| `CI_REGISTRY_USER` | Username for pushing to the registry |
| `CI_REGISTRY_PASSWORD` | Password for pushing |
| `CI_COMMIT_TAG` | The Git tag name, e.g. `v1.2.3` |
| `CI_PIPELINE_IID` | Monotonically increasing pipeline ID (used for ephemeral tags) |
| `CI_SERVER_URL` | Your GitLab instance URL |
| `CI_PROJECT_ID` | Numeric project ID |

### Custom Variables (set in GitLab → Settings → CI/CD → Variables)

| Variable | Description |
|---|---|
| `CI_REGISTRY_TOKEN` | A personal access token with `read_registry` + `write_registry` + `api` scope, used by the cleanup job to call the Registry API |

> **How to create `CI_REGISTRY_TOKEN`:**
> 1. GitLab → User Settings → Access Tokens
> 2. Scopes: `api`, `read_registry`, `write_registry`
> 3. Copy the token, add it as a masked CI variable

---

## Image Names

The pipeline produces images at:

```
registry.gitlab.com/<namespace>/<project>/bot:v1.2.3
registry.gitlab.com/<namespace>/<project>/bot:latest

registry.gitlab.com/<namespace>/<project>/web:v1.2.3
registry.gitlab.com/<namespace>/<project>/web:latest
```

---

## Registry Authentication for Docker Compose Users

To pull private images from your GitLab registry:

```bash
docker login registry.gitlab.com
# Enter your GitLab username and a Personal Access Token (read_registry scope)
```

Then reference the image in `docker-compose.yml`:

```yaml
bot:
  image: registry.gitlab.com/<namespace>/<project>/bot:latest
web:
  image: registry.gitlab.com/<namespace>/<project>/web:latest
```

---

## Enabling the Container Registry on GitLab CE

If using a self-hosted GitLab CE instance, ensure the registry is enabled:

1. Edit `/etc/gitlab/gitlab.rb`:

```ruby
registry_external_url 'https://registry.yourdomain.com'
```

2. Run `gitlab-ctl reconfigure`.

See the [GitLab Container Registry docs](https://docs.gitlab.com/ee/administration/packages/container_registry.html) for full setup.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `unauthorized` on push | Wrong `CI_REGISTRY_PASSWORD` | Check the variable is set and not masked incorrectly |
| Build times out | Large image, no cache | Ensure `--cache-from` can pull — the registry must be reachable from the runner |
| Cleanup job fails | Missing `CI_REGISTRY_TOKEN` | Add the variable in Settings → CI/CD → Variables |
| `docker: not found` | Runner missing Docker executor | Configure the runner with `executor = "docker"` |
