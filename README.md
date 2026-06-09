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
VITE_API_BASE_URL=http://127.0.0.1:4000
```

Credential notes:

- Instagram and Facebook need Meta app/page/account credentials.
- Instagram media publishing needs `PUBLIC_API_BASE_URL` to be a public HTTPS URL so Meta can fetch uploaded media.
- LinkedIn needs an access token and author URN.
- X / Twitter needs app and user access credentials.

When keys are ready, set:

```bash
SOCIAL_DRY_RUN=false
```

Then implement the live calls inside:

```bash
backend/app/social/adapters.py
```

## Current API

- `GET /api/health`: API status.
- `GET /api/platforms`: platform readiness and missing env vars.
- `GET /api/posts`: saved local post history.
- `POST /api/posts`: multipart post creation with optional `media`, `caption`, `textOnly`, and selected `platforms`.

Uploaded files are stored in `backend/data/uploads`. Post history is stored in PostgreSQL when `DATABASE_URL` is set; otherwise it falls back to `backend/data/posts.json`.
# SharePosts
# Social-Media-Tool
