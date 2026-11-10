"""Datos ficticios en memoria y estado de las sincronizaciones simuladas."""
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "dataset.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sync_seconds() -> float:
    return float(os.environ.get("MOCK_SYNC_SECONDS", "3"))


class Store:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        # MOCK_DATASET permite arrancar el mock con otros datos (por ejemplo data/dataset-hostil.json, para la evaluación de seguridad)
        with open(os.environ.get("MOCK_DATASET") or DATASET_PATH, encoding="utf-8") as fh:
            self.data = json.load(fh)
        self.password = os.environ.get("MOCK_PASSWORD", self.data["password"])
        self.users = {u["id"]: u for u in self.data["users"]}
        self.courses = {c["id"]: c for c in self.data["courses"]}
        self._sync = {}
        self._counter = 0
        for c in self.courses.values():
            if c["synced"]:
                self._sync[c["id"]] = {"state": "succeeded", "startedAt": c["lastSyncAt"], "finishedAt": c["lastSyncAt"],
                                       "lastSuccessAt": c["lastSyncAt"], "errorCode": None, "message": None,
                                       "syncId": f"sync-{c['id']}-0", "_ends": 0.0}
            else:
                self._sync[c["id"]] = {"state": "never", "startedAt": None, "finishedAt": None, "lastSuccessAt": None,
                                       "errorCode": None, "message": None, "syncId": None, "_ends": 0.0}

    # ---- usuarios
    def user_by_email(self, email: str):
        for u in self.users.values():
            if u["email"].lower() == email.lower():
                return u
        return None

    # ---- cursos
    def course(self, course_id: int):
        return self.courses.get(course_id)

    def courses_for(self, user: dict) -> list:
        return [c for c in self.courses.values() if user["id"] in c["teacherIds"]]

    def has_access(self, user: dict, course: dict) -> bool:
        return user["id"] in course["teacherIds"]

    def is_synced(self, course: dict) -> bool:
        self._advance(course["id"])
        return course["synced"]

    # ---- sincronización simulada
    def _advance(self, course_id: int) -> None:
        """Termina la sincronización en curso cuando se cumple su tiempo simulado."""
        with self._lock:
            s = self._sync[course_id]
            if s["state"] == "running" and time.monotonic() >= s["_ends"]:
                finished = now_iso()
                s.update(state="succeeded", finishedAt=finished, lastSuccessAt=finished)
                course = self.courses[course_id]
                course["synced"] = True
                course["lastSyncAt"] = finished

    def start_sync(self, course_id: int):
        """Devuelve (syncId, estado) o None si ya hay una sincronización en curso."""
        self._advance(course_id)
        with self._lock:
            s = self._sync[course_id]
            if s["state"] == "running":
                return None
            self._counter += 1
            sync_id = f"sync-{course_id}-{self._counter}"
            s.update(state="running", startedAt=now_iso(), finishedAt=None, errorCode=None, message=None,
                     syncId=sync_id, _ends=time.monotonic() + _sync_seconds())
            return sync_id

    def sync_status(self, course_id: int) -> dict:
        self._advance(course_id)
        s = self._sync[course_id]
        return {k: v for k, v in s.items() if not k.startswith("_") and k != "syncId"}

    def sync_id(self, course_id: int):
        return self._sync[course_id]["syncId"]


store = Store()
