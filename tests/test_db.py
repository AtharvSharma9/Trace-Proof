from pathlib import Path

from db.init import (
    initialize_database,
    verify_database,
    close_connection,
)


def main():
    db_path = Path("test_case.pramaan")

    connection = initialize_database(db_path)

    try:
        if verify_database(connection):
            print("Database initialized successfully.")
        else:
            print("Database initialization failed.")

    finally:
        close_connection(connection)


if __name__ == "__main__":
    main()
