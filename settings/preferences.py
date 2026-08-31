"""Load and save lightweight user preferences."""

from pathlib import Path
import json

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

_DEFAULTS = {
    "tutorial_completed": False,
    "camera_index": None,
    "camera_name": None,
}


def load() -> dict:
    """Load preferences, merging defaults. Never raises."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return {**_DEFAULTS, **data}
    except Exception:
        pass
    return dict(_DEFAULTS)


def save(data: dict) -> None:
    """Merge and save preferences. Never raises."""
    merged = {**_DEFAULTS, **load(), **data}
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(merged, fh, indent=2)
    except Exception:
        pass


def tutorial_completed() -> bool:
    return bool(load().get("tutorial_completed", False))


def set_tutorial_completed(value: bool) -> None:
    save({"tutorial_completed": bool(value)})


def get_camera():
    data = load()
    index = data.get("camera_index")
    name = data.get("camera_name")
    if index is None and name is None:
        return None, None
    return index, name


def set_camera(index, name) -> None:
    save({"camera_index": index, "camera_name": name})
