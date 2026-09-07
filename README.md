# WelcoChat

Single-product rebrand of the former Kaptila portal/backend/website — WelcoChat only, DeskPilot removed.

One deployment, one origin:

- `/` — public marketing site (`site/`, static HTML/CSS/JS)
- `/portal` — client portal SPA (`portal/`, Vue 3 + TypeScript + Vite)
- `/api` — backend (`api/`, FastAPI + SQLAlchemy, MySQL)

## Local development

**API**
```
cd api
python3 -m venv .venv && source .venv/bin/activate
pip install -r app/requirements.txt
cp .env.example .env   # fill in real values
uvicorn app.main:app --reload --port 8000
```

**Portal**
```
cd portal
npm install
npm run dev
```
The portal is served under `/portal/` (see `vite.config.ts` `base`). The dev server proxies `/api` to `http://localhost:8000`.

**Site**
Static files — serve `site/` with any static file server, or point your reverse proxy's `/` at it directly.

## Notes

- `api/.env` holds real secrets (MySQL, JWT, SMTP, Anthropic, Stripe) — never committed. `api/.env.example` is the template.
- Brand: primary `#004A9C`, accent `#F68C36`, background `#FCF8F0`, ink `#111B28`. Font: Manrope.
