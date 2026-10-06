"""Safe command entry point: never print raw connection exceptions."""
import argparse
import json
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["upgrade", "downgrade", "current",
                                          "history", "heads", "revision"])
    parser.add_argument("target", nargs="?")
    parser.add_argument("-m", "--message")
    args = parser.parse_args()
    if args.action == "downgrade" and not args.target:
        parser.error("downgrade requires an explicit target")
    if args.action == "revision" and not args.message:
        parser.error("revision requires -m")
    config = Config(str(ROOT / "alembic.ini"))
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("alembic.runtime.migration").setLevel(logging.INFO)
    try:
        if args.action == "upgrade":
            command.upgrade(config, args.target or "head")
        elif args.action == "downgrade":
            command.downgrade(config, args.target)
        elif args.action == "revision":
            command.revision(config, message=args.message)
        else:
            getattr(command, args.action)(config)
        print(json.dumps({"event": "db.migration.completed", "action": args.action}))
        return 0
    except Exception:
        print(json.dumps({"event": "db.migration.failed", "action": args.action,
                          "message": "Check DB availability, configuration and revision files."}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
