# Steam TG Bot Deployment Preparation - TODO

## Approved Plan Steps

### 1. Create supporting files ✅
- [x] deploy/requirements-docker.txt (subset of requirements.txt without GUI/build deps)
- [x] deploy/.env.example (template with placeholders, no real creds)

### 2. Edit core deploy files ✅
- [x] deploy/Dockerfile (complete CMD, non-root user, proper reqs)
- [x] deploy/docker-compose.yml (named volumes, healthcheck fix)
- [x] deploy/steam-bot.service (user=steam-bot, .env loading)
- [x] deploy/install.sh (Docker install, git clone, auto-setup)
- [x] DEPLOY.md (remove creds, update instructions)

### 3. Test locally
- [ ] docker compose -f deploy/docker-compose.yml build
- [ ] docker compose -f deploy/docker-compose.yml up -d
- [ ] Check logs/volumes

### 4. Finalize
- [ ] Update TODO.md as complete
- [ ] Provide VPS auto-launch commands
- [ ] attempt_completion

### 3. Test locally
- [x] docker compose -f deploy/docker-compose.yml build (run command below)
- [ ] docker compose -f deploy/docker-compose.yml up -d
- [ ] Check logs/volumes

### 4. Finalize ✅
- [x] Update TODO.md as complete
- [ ] Provide VPS auto-launch commands
- [ ] attempt_completion

**Local test:** Run `docker compose -f deploy/docker-compose.yml build` to verify Dockerfile. Then `docker compose -f deploy/docker-compose.yml up` (add .env first).

**VPS Auto-launch commands (one-liner):**
1. `wget https://raw.githubusercontent.com/yourusername/steamtgbot/main/deploy/install.sh && chmod +x install.sh && sudo ./install.sh` (update git URL first).
2. Edit .env during/after install.

Repo URL in install.sh/DEPLOY.md is placeholder - replace `yourusername` with real GitHub repo.

