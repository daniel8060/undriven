#!/usr/bin/env python3
"""CLI commands for Undriven (replaces Flask CLI)."""

import argparse
import getpass
import os

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from backend import config
from backend.database import SessionLocal
from backend.models import User, SavedCar


def create_user(args):
    username = args.username
    password = getpass.getpass("Password: ")
    password2 = getpass.getpass("Confirm password: ")
    if password != password2:
        print("Error: passwords do not match.", file=sys.stderr)
        sys.exit(1)

    session = SessionLocal()
    try:
        if session.query(User).filter_by(username=username).first():
            print(f"Error: username '{username}' already exists.", file=sys.stderr)
            sys.exit(1)
        u = User(username=username)
        u.set_password(password)
        session.add(u)
        session.commit()
        print(f"Created user '{username}' (id={u.id}).")
    finally:
        session.close()


def seed_cars(args):
    username = args.username
    session = SessionLocal()
    try:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            print(f"Error: user '{username}' not found.", file=sys.stderr)
            sys.exit(1)
        added = 0
        for i, (name, spec) in enumerate(config.CARS.items()):
            if session.query(SavedCar).filter_by(user_id=user.id, name=name).first():
                print(f"  skip '{name}' (already exists)")
                continue
            has_default = session.query(SavedCar).filter_by(user_id=user.id, is_default=True).first()
            car = SavedCar(
                user_id=user.id,
                name=name,
                mpg=spec["mpg"],
                fuel_type=spec.get("fuel_type", "gasoline"),
                is_default=(i == 0 and not has_default),
                sort_order=session.query(SavedCar).filter_by(user_id=user.id).count(),
            )
            session.add(car)
            added += 1
            default_tag = " [default]" if car.is_default else ""
            print(f"  added '{name}' ({spec['mpg']} mpg, {spec.get('fuel_type', 'gasoline')}){default_tag}")
        session.commit()
        print(f"Done. {added} car(s) added for '{username}'.")
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(prog="undriven", description="Undriven CLI")
    sub = parser.add_subparsers(dest="command")

    p_user = sub.add_parser("create-user", help="Create a new user account")
    p_user.add_argument("username")
    p_user.set_defaults(func=create_user)

    p_cars = sub.add_parser("seed-cars", help="Seed saved cars from config for a user")
    p_cars.add_argument("username")
    p_cars.set_defaults(func=seed_cars)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
