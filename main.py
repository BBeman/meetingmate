from fastapi import FastAPI

app = FastAPI(title="MeetingMate")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
