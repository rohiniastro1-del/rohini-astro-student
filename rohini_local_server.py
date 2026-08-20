from __future__ import annotations

import sys
import traceback
from pathlib import Path

from werkzeug.serving import make_server

from app import app


APP_ROOT = Path(__file__).resolve().parent
SERVER_CRASH_LOG = APP_ROOT / ".rohini-server.crash.log"


def main() -> None:
    port = int(sys.argv[1])
    server = make_server("127.0.0.1", port, app, threaded=True)
    server.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        SERVER_CRASH_LOG.write_text(traceback.format_exc(), encoding="utf-8")
        raise
