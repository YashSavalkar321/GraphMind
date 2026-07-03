# Deploying GraphMind

Target stack (free tier):

| Layer     | Service                | Notes                                           |
| --------- | ---------------------- | ----------------------------------------------- |
| Frontend  | **Vercel**             | Static Vite build, global CDN                   |
| Backend   | **Hugging Face Spaces** (Docker) | 16 GB RAM free — fits PyTorch/embeddings |
| Database  | **Neo4j Aura Free**    | Managed, `neo4j+s://` connection                |

> **Architecture constraint:** the backend keeps each user's graph **in memory** (CQRS engine).
> Run **one instance / one worker** — never scale to multiple replicas or `--workers > 1`.
> Losing memory on restart is fine: sessions rehydrate from Neo4j on the next login.

---

## 0. Before you start — rotate secrets 🔑

The keys currently in `.env` (Groq, Gemini, Clerk) were committed to your working tree and
shared in chat. **Regenerate all of them** and only ever set the new values as platform secrets:

- Groq → https://console.groq.com/keys
- Gemini → https://aistudio.google.com/apikey
- Clerk (if used) → Clerk dashboard → API keys
- `JWT_SECRET` → generate a fresh one: `python -c "import secrets; print(secrets.token_urlsafe(48))"`

Never commit a real `.env`. It is git-ignored; use `.env.example` as the template.

---

## 1. Neo4j Aura Free

1. Create a free instance at https://console.neo4j.io → **New Instance → AuraDB Free**.
2. On creation you get a **connection URI** (`neo4j+s://<id>.databases.neo4j.io`) and a generated
   **password** — download/save the credentials file, the password is shown only once.
3. Keep these for step 2:
   - `NEO4J_URI = neo4j+s://<id>.databases.neo4j.io`
   - `NEO4J_USER = neo4j`
   - `NEO4J_PASSWORD = <generated>`

> ⚠️ Aura Free **pauses after 3 days idle** (resume with one click) and is **deleted after 30 days**
> of no use. Fine for a demo; move to a paid tier or self-hosted Neo4j for anything long-lived.

---

## 2. Backend → Hugging Face Space (Docker)

1. Create a Space: https://huggingface.co/new-space → **SDK: Docker → Blank**. Note its URL:
   `https://huggingface.co/spaces/<user>/<space>` and its **app URL** `https://<user>-<space>.hf.space`.
2. Push this repo's backend to the Space. The repo already contains a root **`Dockerfile`** that
   builds only `backend/` with CPU-only torch and pre-bakes the embedding model.
   - Easiest: add the Space as a git remote and push, **or** connect the Space to your GitHub repo
     (Space Settings → *Link to a GitHub repository*).
3. The Space's **`README.md`** must begin with this front-matter (the `app_port` must match the
   Dockerfile's `7860`):

   ```yaml
   ---
   title: GraphMind API
   emoji: 🧠
   colorFrom: indigo
   colorTo: purple
   sdk: docker
   app_port: 7860
   pinned: false
   ---
   ```

4. Set env vars under **Space Settings → Variables and secrets** (mark keys as *Secret*):

   | Name             | Value                                             | Secret |
   | ---------------- | ------------------------------------------------- | :----: |
   | `APP_ENV`        | `production`                                      |        |
   | `NEO4J_URI`      | `neo4j+s://<id>.databases.neo4j.io`               |   ✓    |
   | `NEO4J_USER`     | `neo4j`                                            |        |
   | `NEO4J_PASSWORD` | *(Aura password)*                                 |   ✓    |
   | `GROQ_API_KEY`   | *(new key)*                                        |   ✓    |
   | `GEMINI_API_KEY` | *(new key)*                                        |   ✓    |
   | `LLM_MODEL`      | `llama-3.3-70b-versatile`                          |        |
   | `JWT_SECRET`     | *(new random secret)*                             |   ✓    |
   | `CORS_ORIGINS`   | *(set in step 4 — your Vercel URL)*               |        |

   Do **not** set `PORT` — HF provides 7860 via `app_port`.

5. The first build takes several minutes (installs torch + bakes the model). When it's live,
   check `https://<user>-<space>.hf.space/health` → `{"status":"ok","neo4j":true,...}`.

> ⚠️ Free Spaces **sleep after ~48 h idle** and are **public**. First request after sleep is slow
> while the container wakes.

---

## 3. Frontend → Vercel

1. Import the repo at https://vercel.com/new.
2. **Root Directory → `frontend`** (important — the app lives in the subfolder). Framework
   auto-detects as **Vite**; build `npm run build`, output `dist` (already set in `frontend/vercel.json`).
3. Add an environment variable:
   - `VITE_API_URL = https://<user>-<space>.hf.space`  *(your Space app URL from step 2, no trailing slash)*
4. Deploy. Note the resulting URL, e.g. `https://graphmind.vercel.app`.

---

## 4. Close the loop (CORS)

The two services reference each other, so finish the wiring:

1. Back on the **HF Space**, set `CORS_ORIGINS = https://graphmind.vercel.app` (your Vercel URL,
   exact origin, no trailing slash — comma-separate if you have several).
2. **Restart** the Space (Settings → *Factory reboot* or push a commit) so it picks up the new value.
3. Open the Vercel URL, sign up, ingest a note, and chat. The navbar should show **Online** and
   answers should cite memory.

### Env-var quick reference

| Where          | Variable        | Points at                          |
| -------------- | --------------- | ---------------------------------- |
| Vercel         | `VITE_API_URL`  | the HF Space app URL               |
| HF Space       | `CORS_ORIGINS`  | the Vercel URL                     |
| HF Space       | `NEO4J_URI` …   | Neo4j Aura                         |

---

## Verifying

```bash
# Backend health
curl https://<user>-<space>.hf.space/health

# Signup
curl -X POST https://<user>-<space>.hf.space/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name":"A","email":"a@b.com","password":"secret123"}'
```

## Troubleshooting

| Symptom | Cause / Fix |
| ------- | ----------- |
| Frontend loads but "Offline" / API 404 | `VITE_API_URL` missing or wrong on Vercel → set it and redeploy |
| Browser console: CORS blocked | `CORS_ORIGINS` on the Space doesn't exactly match the Vercel origin → fix + restart Space |
| `/health` shows `"neo4j":false` | Neo4j creds wrong, or Aura instance paused → check vars / resume Aura |
| First request very slow | Space was asleep (waking) — expected on free tier |
| `LLM call failed` | `GROQ_API_KEY` / `GEMINI_API_KEY` invalid → rotate and re-set |
