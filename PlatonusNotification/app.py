import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from send_notification import fetch_notifications


app = FastAPI(title="Platonus Notifications API")


class Credentials(BaseModel):
    iin: str | None = None
    code: str | None = None
    username: str | None = None
    password: str | None = None


@app.post("/notifications")
def get_notifications(credentials: Credentials):
    # Логин и пароль берём только из переменных окружения (.env)
    username = os.getenv("PLATONUS_USERNAME")
    password = os.getenv("PLATONUS_PASSWORD")
    iin = credentials.iin
    code = credentials.code

    if not username or not password:
        raise HTTPException(
            status_code=400,
            detail=(
                "Credentials not provided. Set PLATONUS_USERNAME and PLATONUS_PASSWORD "
                "environment variables."
            ),
        )

    try:
        response = fetch_notifications(username, password, iin, code)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=401, detail=str(exc)
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch notifications: {exc}"
        ) from exc

    return {
        "html": response.get("html"),
        "iin": response.get("iin"),
        "fio": response.get("fio"),
        "student_id": response.get("student_id"),
        "row": response.get("row"),
    }

