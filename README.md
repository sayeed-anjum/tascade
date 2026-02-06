# Tascade (Vertical Slice)

Minimal FastAPI vertical slice implementing:
- task/dependency creation with cycle rejection
- ready queue, claim, heartbeat
- plan change-set create/apply
- material-change invalidation for claimed/reserved tasks
- task execution snapshot capture on claim/start

## Run Tests

```bash
pytest -q
```

## Run API

```bash
export TASCADE_DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5432/tascade'
uvicorn app.main:app --reload
```

If `TASCADE_DATABASE_URL` is not set, the app defaults to:

`postgresql+psycopg://postgres:postgres@localhost:5432/tascade`
