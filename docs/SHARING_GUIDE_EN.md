# Sharing ASGP — Choose One Method

## Short answer

**You do not need to perform every method. Choose one sharing method for your goal:**

| Goal | Recommended method | Verdict |
|---|---|---|
| Collaborate with teammates who will modify the project | GitHub | Best and recommended |
| Send one fixed copy to a supervisor or friend | Clean ZIP | Easiest, poor for ongoing collaboration |
| Distribute a runnable release without source code | Docker images | Useful for delivery, more advanced |

Docker is primarily a **way to run the project**, not necessarily the way to share its source. The recommended combination is GitHub for sharing and Docker Compose for consistent execution.

# Method 1: GitHub — Recommended for the team

## Use it when

- Multiple teammates will modify the project.
- You need version history, branches, reviews, or rollback.
- You want everyone to receive updates without downloading a full new copy.

## One-time owner setup

Create an empty private GitHub repository, open PowerShell in `D:\Grad`, and run:

```powershell
git init
git add .
git status
git commit -m "Complete ASGP graduation project"
git branch -M main
git remote add origin https://github.com/USERNAME/asgp.git
git push -u origin main
```

Replace `USERNAME` with your account. Review `git status` before committing. Never commit `.env`, API keys, private keys, or local databases.

## Teammate steps

```powershell
git clone https://github.com/USERNAME/asgp.git
cd asgp
docker-compose up --build
```

Open:

- Dashboard: `http://127.0.0.1:4173`
- API documentation: `http://127.0.0.1:8000/docs`

## Advantages

- Best option for teamwork.
- Complete change history and rollback.
- Branches and pull requests support review.
- Teammates receive updates with `git pull`.
- A private repository can be restricted to your group.

## Disadvantages

- Requires basic Git knowledge.
- Merge conflicts are possible when two people edit the same lines.
- Committing a secret by mistake is a serious risk.
- The first Docker build needs internet access and may take time.

## Verdict

**Use this method for ASGP development.** Share the source through a private GitHub repository and run it with Docker Compose.

# Method 2: Clean ZIP — Best for a one-time handoff

## Use it when

- A supervisor needs a fixed snapshot.
- A friend only needs to inspect or run the project.
- You do not want to configure GitHub yet.
- You are transferring the project by Drive, email, or USB.

## Preferred ZIP creation with Git

After creating a commit:

```powershell
git archive --format=zip --output=ASGP-project.zip HEAD
```

This includes tracked project files while excluding ignored local environments and secrets.

## ZIP creation without Git

1. Create a separate copy of the project folder.
2. Remove the following from the **copy only**:

```text
.venv/
node_modules/
frontend/dist/
__pycache__/
.pytest_cache/
.ruff_cache/
.env
*.db
```

3. Check that no API key or private key remains.
4. Compress the clean copy as `ASGP-project.zip`.

## Recipient steps

Extract the archive, then run:

```powershell
cd ASGP-project
docker-compose up --build
```

Open `http://127.0.0.1:4173`.

## Advantages

- Very simple.
- Good for final submission or USB transfer.
- Does not require a GitHub account.

## Disadvantages

- No useful version history.
- Every update requires a new archive.
- Teams quickly accumulate confusing `final`, `final2`, and `final-last` copies.
- Combining changes from several people is difficult.
- Compressing the working directory without cleaning can expose secrets or produce a huge archive.

## Verdict

Good for a supervisor or final snapshot, but **not recommended for daily team development**.

# Method 3: Docker images — Runnable release without source

## Use it when

- A recipient should run the product without receiving source code.
- You need fixed backend and frontend release versions.
- You have access to Docker Hub or GitHub Container Registry.

Build and publish tagged images:

```powershell
docker build -t USERNAME/asgp-backend:1.0 ./backend
docker build -t USERNAME/asgp-frontend:1.0 ./frontend
docker login
docker push USERNAME/asgp-backend:1.0
docker push USERNAME/asgp-frontend:1.0
```

Provide a Compose file using `image:` instead of `build:`. The recipient runs:

```powershell
docker-compose pull
docker-compose up
```

## Advantages

- Nearly identical runtime environment on different machines.
- The recipient does not install Python or Node dependencies.
- Source code does not have to be distributed.
- Appropriate for tagged product releases.

## Disadvantages

- More complicated than GitHub or ZIP.
- Requires a registry, login, and tag management.
- Images can be large.
- Not useful for teammates who must edit the source.
- PostgreSQL data remains a separate volume.
- Environment variables and secrets still require separate management.

## Verdict

Useful for later product delivery, but **not the first choice for a graduation team collaborating on code**.

# Optional transport: Drive or USB

Drive and USB are only transport mechanisms. Create a clean ZIP using Method 2, then transfer it. They inherit all advantages and disadvantages of ZIP-based sharing.

# Running without Docker

This is an alternative runtime path, regardless of whether the source arrived through GitHub or ZIP:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:ASGP_DATABASE_URL = "sqlite+pysqlite:///./asgp.db"
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

In a second terminal from the repository root:

```powershell
cd frontend
pnpm install
pnpm dev
```

This path is useful for development but requires Python, Node.js, pnpm, and more manual setup than Docker.

# Final recommendation

Follow only this plan:

1. Create a private GitHub repository.
2. Upload the source after checking for secrets.
3. Add teammates as collaborators.
4. Give each teammate a separate branch.
5. Run the project with `docker-compose up --build`.
6. For final submission, create a GitHub Release or clean ZIP with `git archive`.

This gives the team proper collaboration while Docker standardizes local execution.

# Pre-sharing checklist

- `.env` is not included.
- No API or private keys are present.
- `.venv` and `node_modules` are excluded.
- `docker-compose config` passes.
- Backend tests and frontend build pass.
- `evaluation/latest/REPORT.md` and `docs/` are included.
- Every teammate understands that ASGP governs only tools routed through its SDK or gateway.
