"""Run from any directory with this project's virtual-environment Python."""
import json
import sys

from app.database import connect_db


def main():
    try:
        with connect_db() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                assert cursor.fetchone() == (1,)
                cursor.execute("SHOW server_version")
                version = cursor.fetchone()[0]
        print(json.dumps({"event": "db.connection.checked", "status": "ok",
                          "server_version": version}))
        return 0
    except Exception:
        # Connection exceptions can contain sensitive settings; omit raw details.
        print(json.dumps({"event": "db.connection.failed",
                          "message": "Check Docker status and local DB settings."}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
