from __future__ import annotations

import json
import mimetypes
from copy import deepcopy
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_FILE = DATA_DIR / "logbook.json"
HOST = "127.0.0.1"
PORT = 8080


DEFAULT_LOGBOOK = {
    "species": [
        "Lake Trout",
        "Largemouth Bass",
        "Smallmouth Bass",
        "Chinook Salmon",
        "Coho Salmon",
        "Rainbow Trout",
        "Brown Trout",
        "Walleye",
        "Northern Pike",
        "Muskie",
        "Rock Bass",
        "Perch",
        "Crappie",
        "Bluegill",
    ],
    "methods": [
        "Trolling",
        "Casting",
        "Jigging",
        "Fly Fishing",
        "Bait Fishing",
        "Ice Fishing",
    ],
    "lureTypes": [
        "Spoon",
        "Fly",
        "Meat Rig",
        "Crankbait",
        "Spinner",
        "Jig",
        "Soft Plastic",
        "Plug",
        "Swimbait",
        "Flasher/Fly",
        "Jerkbait",
        "Topwater",
        "Blade Bait"
        "Other",
    ],
    "flasherTypes": [
        "Paddle",
        "Spin Doctor",
    ],
    "lures": [],
    "flashers": [],
    "people": [],
    "locations": [],
    "trips": [],
}


def normalize_logbook(payload: dict | None = None) -> dict:
    normalized = deepcopy(DEFAULT_LOGBOOK)
    if isinstance(payload, dict):
        normalized.update(payload)

    normalized["methods"] = deepcopy(DEFAULT_LOGBOOK["methods"])
    normalized.pop("tripTypes", None)

    for key in ("species", "lureTypes", "flasherTypes", "lures", "flashers", "people", "locations", "trips"):
        if not isinstance(normalized.get(key), list):
            normalized[key] = deepcopy(DEFAULT_LOGBOOK[key])

    known_people = {person.get("id"): person for person in normalized["people"] if isinstance(person, dict) and person.get("id")}
    for trip in normalized["trips"]:
        if not isinstance(trip, dict):
            continue
        for person in trip.get("people", []):
            if isinstance(person, dict) and person.get("id") and person.get("name") and person.get("id") not in known_people:
                known_people[person["id"]] = {"id": person["id"], "name": person["name"]}
    normalized["people"] = list(known_people.values())
    known_locations = {str(location).strip().lower(): str(location).strip() for location in normalized["locations"] if str(location).strip()}
    for trip in normalized["trips"]:
        if isinstance(trip, dict) and str(trip.get("location", "")).strip():
            location = str(trip["location"]).strip()
            known_locations.setdefault(location.lower(), location)
    normalized["locations"] = list(known_locations.values())

    return normalized


def read_logbook() -> dict:
    if not DATA_FILE.exists():
        return normalize_logbook()

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
    except json.JSONDecodeError:
        return normalize_logbook()

    return normalize_logbook(loaded)


def write_logbook(payload: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(normalize_logbook(payload), file, indent=2)


class LogbookHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/logbook":
            self.send_json(read_logbook())
            return

        if path == "/api/export":
            payload = json.dumps(read_logbook(), indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Disposition", "attachment; filename=fishing-logbook.json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        if path == "/":
            self.path = "/index.html"

        super().do_GET()

    def do_PUT(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/logbook":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            self.send_error(400, "Invalid JSON")
            return

        if (
            not isinstance(payload.get("trips"), list)
            or not isinstance(payload.get("lures"), list)
            or not isinstance(payload.get("flashers"), list)
            or not isinstance(payload.get("people", []), list)
        ):
            self.send_error(400, "Logbook must include trips, lures, flashers, and people lists")
            return

        write_logbook(normalize_logbook(payload))
        self.send_json({"ok": True})

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def guess_type(self, path: str) -> str:
        if path.endswith(".js"):
            return "text/javascript"
        return mimetypes.guess_type(path)[0] or "application/octet-stream"


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        write_logbook(DEFAULT_LOGBOOK)

    server = ThreadingHTTPServer((HOST, PORT), LogbookHandler)
    print(f"Fishing Logbook running at http://{HOST}:{PORT}")
    print(f"Data file: {DATA_FILE}")
    server.serve_forever()


if __name__ == "__main__":
    main()
