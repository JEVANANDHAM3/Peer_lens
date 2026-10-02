from __future__ import annotations

from threading import Lock
from typing import Any, Dict

try:
    from backend.database import delete_all_statuses, get_status_by_id, save_status
except Exception:  # pragma: no cover
    save_status = None
    get_status_by_id = None
    delete_all_statuses = None

_PROGRESS_STORE: Dict[str, Dict[str, Any]] = {}
_PROGRESS_LOCK = Lock()


def record_status(review_id: str, status: str, message: str | None = None, **extra: Any) -> Dict[str, Any]:
    if not review_id:
        return {}

    with _PROGRESS_LOCK:
        entry = _PROGRESS_STORE.setdefault(review_id, {"review_id": review_id})
        entry["status"] = status
        if message is not None:
            entry["message"] = message
        for key, value in extra.items():
            entry[key] = value

        if save_status is not None:
            try:
                save_status(
                    review_id=review_id,
                    status=status,
                    message=message or entry.get("message", ""),
                    paper_id=entry.get("paper_id"),
                    review_mode=entry.get("review_mode"),
                )
            except Exception:
                pass

        return dict(entry)


def get_status_snapshot(review_id: str) -> Dict[str, Any]:
    with _PROGRESS_LOCK:
        if review_id in _PROGRESS_STORE:
            return dict(_PROGRESS_STORE[review_id])

    if get_status_by_id is not None:
        try:
            db_status = get_status_by_id(review_id)
            if db_status:
                with _PROGRESS_LOCK:
                    _PROGRESS_STORE[review_id] = db_status
                return dict(db_status)
        except Exception:
            pass

    return {"review_id": review_id, "status": "running", "message": "Review started."}


def clear_statuses() -> None:
    with _PROGRESS_LOCK:
        _PROGRESS_STORE.clear()
    if delete_all_statuses is not None:
        try:
            delete_all_statuses()
        except Exception:
            pass

