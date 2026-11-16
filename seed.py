import sys

from sqlalchemy.orm import Session

from models import Base, Ticket, User, engine

USER_NAMES = ["Ana", "Luis", "Marta"]


def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        sys.exit("Uso: python3 seed.py <número_inicial>")
    count = int(sys.argv[1])

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all(User(name=name) for name in USER_NAMES)
        session.add_all(Ticket() for _ in range(count))
        session.commit()

    print(f"{len(USER_NAMES)} usuarios y {count} tickets disponibles creados")


if __name__ == "__main__":
    main()
