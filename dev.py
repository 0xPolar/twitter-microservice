#!/usr/bin/env python3
"""Manage the rootless Podman development environment using Python's standard library."""

import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
COMPOSE = ["podman-compose", "-p", "twitter-dev", "-f", str(ROOT / "docker-compose.yml")]
SERVICES = {"users": "user-service", "tweets": "tweet-service", "feed": "feed-service", "search": "search-service"}

ENV_TEMPLATE = """# Container connection settings; host port overrides are separate below.
DB_DATABASE=twitter_clone
DB_USERNAME=twitter_dev
DB_PASSWORD=twitter_dev_password
DB_HOST=postgres
DB_PORT=5432
JWT_SECRET=REPLACE_WITH_RANDOM_SECRET
JWT_ALGO=HS256
JAEGER=jaeger:4317
RABBITMQ_USERNAME=twitter_dev
RABBITMQ_PASSWORD=twitter_dev_password
RABBITMQ_HOST=rabbitmq
RABBITMQ_URL=amqp://twitter_dev:twitter_dev_password@rabbitmq:5672
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_ADDRESS=redis:6379
ELASTICSEARCH_URL=http://elasticsearch:9200
USER_SERVICE_GRPC_TARGET=user-service:50051
USERS_GRPC_ADDRESS=user-service:50051
TWEET_SERVICE_GRPC_TARGET=tweet-service:50051

# Host access only; application containers use the settings above.
POSTGRES_HOST_PORT=5432
REDIS_HOST_PORT=6379
ELASTICSEARCH_HOST_PORT=9200
RABBITMQ_HOST_PORT=5672
RABBITMQ_UI_PORT=15672
JAEGER_UI_PORT=16686
USERS_HTTP_PORT=5000
USERS_GRPC_PORT=50050
TWEETS_HTTP_PORT=5001
TWEETS_GRPC_PORT=50051
FEED_HTTP_PORT=5002
SEARCH_HTTP_PORT=5003
"""


def compose(*args):
    subprocess.run([*COMPOSE, *args], cwd=ROOT, check=True)


def initialize():
    path = ROOT / ".env"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print(".env already exists; left unchanged.")
        return
    with os.fdopen(fd, "w") as stream:
        stream.write(ENV_TEMPLATE.replace("REPLACE_WITH_RANDOM_SECRET", secrets.token_urlsafe(48)))
    print("Created .env for local development.")


def check_health():
    settings = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            settings[key.strip()] = value.strip().strip("\"'")
    messages = []
    for name, variable, default in [
        ("users", "USERS_HTTP_PORT", 5000),
        ("tweets", "TWEETS_HTTP_PORT", 5001),
        ("feed", "FEED_HTTP_PORT", 5002),
        ("search", "SEARCH_HTTP_PORT", 5003),
    ]:
        port = int(os.environ.get(variable, settings.get(variable, default)))
        with urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as response:
            if json.load(response).get("status") != "healthy":
                raise ValueError(f"{name}: unhealthy response")
        with urlopen(f"http://127.0.0.1:{port}/openapi.json", timeout=3) as response:
            if not json.load(response).get("paths"):
                raise ValueError(f"{name}: missing API paths")
        messages.append(f"{name}: health and OpenAPI OK")
    for variable, default in [("USERS_GRPC_PORT", 50050), ("TWEETS_GRPC_PORT", 50051)]:
        port = int(os.environ.get(variable, settings.get(variable, default)))
        with socket.create_connection(("127.0.0.1", port), timeout=3):
            pass
        messages.append(f"{variable}: TCP listener OK")
    return messages


def smoke():
    deadline = time.monotonic() + 60
    while True:
        try:
            messages = check_health()
            break
        except (URLError, OSError, ValueError) as error:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Stack not ready within 60 seconds: {error}") from error
            time.sleep(1)
    print("\n".join(messages))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, epilog="Example: python3 dev.py logs user-service")
    parser.add_argument("command", nargs="?", default="help", choices=[
        "init", "up", "down", "logs", "ps", "build", "rebuild", "test", "reset", "config", "check", "help"
    ])
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Service names or arguments passed to Compose/pytest")
    options = parser.parse_args(argv)
    command, args = options.command, options.args
    if command in {"init", "check", "help"} and args:
        parser.error(f"{command} does not accept extra arguments")
    if command == "help":
        parser.print_help()
    elif command == "init":
        initialize()
    elif command == "check":
        smoke()
    elif command == "up":
        compose("up", "--build", "-d", *args)
        if not args:
            smoke()
    elif command == "logs":
        compose("logs", "-f", *args)
    elif command in {"down", "ps", "build", "config"}:
        compose(command, *args)
    elif command == "rebuild":
        if not args:
            parser.error("rebuild requires a service name")
        compose("up", "-d", "--build", "--force-recreate", *args)
    elif command == "reset":
        if args != ["--confirm-delete-dev-data"]:
            parser.error("reset deletes development volumes; use reset --confirm-delete-dev-data")
        compose("down", "--volumes")
    elif command == "test":
        if not args or args[0] not in SERVICES:
            parser.error("test requires users, tweets, feed, or search, followed by optional pytest arguments")
        # Separate process without application startup; block unmocked access to dev data.
        environment = {
            "DB_HOST": "127.0.0.1", "DB_DATABASE": "twitter_tests",
            "REDIS_HOST": "127.0.0.1", "REDIS_ADDRESS": "127.0.0.1:6379",
            "RABBITMQ_HOST": "127.0.0.1", "RABBITMQ_URL": "amqp://test:test@127.0.0.1:5672",
            "ELASTICSEARCH_URL": "http://127.0.0.1:9200",
            "USER_SERVICE_GRPC_TARGET": "127.0.0.1:50051",
            "TWEET_SERVICE_GRPC_TARGET": "127.0.0.1:50051",
        }
        flags = [item for key, value in environment.items() for item in ("-e", f"{key}={value}")]
        compose("run", "--rm", "--no-deps", *flags, SERVICES[args[0]],
                "python", "-m", "pytest", "-p", "no:cacheprovider", "tests/", *args[1:])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
    except (OSError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
