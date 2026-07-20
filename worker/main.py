"""Temporary worker process entry point; Task 5 supplies its work loop."""

from threading import Event


def main() -> None:
    print("Worker placeholder started; Task 5 will add job processing.", flush=True)
    Event().wait()


if __name__ == "__main__":
    main()
