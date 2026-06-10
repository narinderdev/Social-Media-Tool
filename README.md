# Social Media Tool

One local dashboard to compose a post once and send it to Instagram, Facebook, LinkedIn, and X / Twitter.

The app is ready for local use in `SOCIAL_DRY_RUN=true` mode. Later, add real API keys in `backend/.env` and replace each adapter placeholder in `backend/app/social/adapters.py` with the approved platform publish calls.

## Projects

- `backend`: FastAPI API for uploads, post validation, local history, and social platform adapters.
- `frontend`: Vite React app for media/text composition, platform selection, preview, and history.

## Run Locally

Install dependencies:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install
```

Start the backend:

```bash
cd backend
source .venv/bin/activate
python run.py
```

Start the frontend in another terminal:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`.

After login:

- `http://localhost:5173/dashboard`: compose and publish posts.
- `http://localhost:5173/posts`: view saved post history from PostgreSQL.
- `http://localhost:5173/scheduled`: view upcoming scheduled posts.

## API Keys Later

Backend env keys in `backend/.env`:

```bash
PORT=4000
BACKEND_HOST=127.0.0.1
FRONTEND_ORIGIN=http://localhost:5173
PUBLIC_API_BASE_URL=http://localhost:4000
DATABASE_URL=postgresql://apnitormacmini3@localhost:5432/shared_posts_db
ADMIN_USER=hr@apnitor.com
ADMIN_PASSWORD=Apnitor@1
SOCIAL_DRY_RUN=true
META_GRAPH_API_VERSION=v24.0

META_APP_ID=
META_APP_SECRET=
INSTAGRAM_ACCOUNT_ID=
INSTAGRAM_ACCESS_TOKEN=
FACEBOOK_PAGE_ID=
FACEBOOK_PAGE_ACCESS_TOKEN=
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_AUTHOR_URN=
LINKEDIN_API_VERSION=202605
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_TOKEN_SECRET=
TWITTER_BEARER_TOKEN=
```

Frontend env key in `frontend/.env`:

```bash
VITE_API_BASE_URL=http://localhost:4000
```

Credential notes:

- Instagram and Facebook need Meta app/page/account credentials.
- Instagram media publishing needs `PUBLIC_API_BASE_URL` to be a public HTTPS URL so Meta can fetch uploaded media.
- LinkedIn needs an access token and author URN.
- X / Twitter needs app and user access credentials.
- Published post analytics refresh automatically every 3 hours in the background and are saved in PostgreSQL under the `post_stats` table.
- Opening a post stats modal starts a live 1-second refresh for the selected platforms until the modal is closed.
- Instagram/Facebook/X can return impressions, views, reach, engagement, reactions, comments, shares, clicks, saves, or bookmarks when the account token has the required platform permissions.
- LinkedIn returns reactions and comments through social metadata with normal social-feed permissions; impressions and views require LinkedIn's restricted analytics access.

When keys are ready, set:

```bash
SOCIAL_DRY_RUN=false
```

### Multiple Brand Accounts

Use account profiles when the same dashboard must post for more than one brand, for example
`Glowante` and `Apnitor`.

Existing unprefixed credentials are used for the default account, so your current `backend/.env`
can keep working for Glowante:

```bash
SOCIAL_ACCOUNTS=glowante,apnitor
DEFAULT_SOCIAL_ACCOUNT=glowante
SOCIAL_ACCOUNT_GLOWANTE_LABEL=Glowante
SOCIAL_ACCOUNT_APNITOR_LABEL=Apnitor
```

Add Apnitor credentials with this prefix pattern:

```bash
SOCIAL_ACCOUNT_APNITOR_INSTAGRAM_ACCOUNT_ID=
SOCIAL_ACCOUNT_APNITOR_INSTAGRAM_ACCESS_TOKEN=
SOCIAL_ACCOUNT_APNITOR_FACEBOOK_PAGE_ID=
SOCIAL_ACCOUNT_APNITOR_FACEBOOK_PAGE_ACCESS_TOKEN=
SOCIAL_ACCOUNT_APNITOR_LINKEDIN_ACCESS_TOKEN=
SOCIAL_ACCOUNT_APNITOR_LINKEDIN_AUTHOR_URN=
SOCIAL_ACCOUNT_APNITOR_TWITTER_API_KEY=
SOCIAL_ACCOUNT_APNITOR_TWITTER_API_SECRET=
SOCIAL_ACCOUNT_APNITOR_TWITTER_ACCESS_TOKEN=
SOCIAL_ACCOUNT_APNITOR_TWITTER_ACCESS_TOKEN_SECRET=
```

The frontend shows a top-level `Select account` control on Posts, History, and Scheduled. The
selected account filters history/scheduled posts and is used by all four platform adapters.

## Current API

- `GET /api/health`: API status.
- `GET /api/accounts`: configured social account profiles and per-platform readiness.
- `GET /api/platforms`: platform readiness and missing env vars.
- `GET /api/posts`: saved local post history.
- `POST /api/posts`: multipart post creation with optional `media`, `caption`, `textOnly`, and selected `platforms`.

Uploaded files are stored in `backend/data/uploads`. Post history is stored in PostgreSQL when `DATABASE_URL` is set; otherwise it falls back to `backend/data/posts.json`.
# SharePosts
# Social-Media-Tool
