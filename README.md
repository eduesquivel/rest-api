# REST API

A small ticket sale and refund API built with Python, FastAPI, SQLAlchemy and PostgreSQL. Its main goal is to make sure a ticket can never be sold twice, even when several purchases arrive at the same time.

## Running it locally

Requirements: Python 3.13+, [uv](https://docs.astral.sh/uv/) and a PostgreSQL instance (the steps below use Docker).

1. Start PostgreSQL:

   ```bash
   docker run --name db -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres
   ```

2. Create a `.env` file in the project root pointing to that database:

   ```
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
   ```

3. Install the dependencies:

   ```bash
   uv sync
   ```

4. Create the tables and seed them with the number of tickets you want, for example 30:

   ```bash
   uv run python3 seed.py 30
   ```

5. Start the API:

   ```bash
   uv run fastapi dev main.py
   ```

The API is now on http://127.0.0.1:8000, with interactive docs on http://127.0.0.1:8000/docs.

## Endpoints

| Method | Path | Body | Description |
|---|---|---|---|
| `GET` | `/tickets` | – | Lists the available tickets. |
| `POST` | `/tickets/buy/{ticket_id}` | `{"user_id": 1}` | Sells the ticket to that user. |
| `POST` | `/tickets/refund/{ticket_id}` | `{"user_id": 1}` | Refunds the ticket, making it available again. |

Responses:

- `200`: the operation succeeded.
- `404`: the ticket does not exist, or the user does not exist (purchase only).
- `409`: the ticket is already sold (purchase) or is not sold (refund).
- `403`: the ticket belongs to another user (refund only).
- `422`: the request is malformed.

Example:

```bash
curl -X POST http://127.0.0.1:8000/tickets/buy/1 \
  -H "Content-Type: application/json" -d '{"user_id": 1}'
```

## Architecture decisions

### Tickets are rows created up front by `seed.py`

There is no stock counter. `seed.py` writes the whole database: it drops and recreates the `users` and `tickets` tables, then inserts three users (Ana, Luis and Marta, with ids 1, 2 and 3) and as many tickets as requested.

Each ticket is one row with a nullable `user_id` foreign key:

- `user_id IS NULL` means the ticket is available.
- Otherwise `user_id` is the owner.

This keeps the model small and makes overselling impossible by construction. The stock is the set of rows itself, so there is no counter to keep in sync, and a ticket can only have one owner because it only has one `user_id` column. The API never creates or deletes tickets; buying and refunding only change that column.

Because the seed drops the tables, running it again resets all purchases.

### Concurrency is handled with a row lock

Both the purchase and the refund read the ticket with `SELECT ... FOR UPDATE` (`with_for_update()` in SQLAlchemy), check its state, update it and commit, all in one transaction.

If two requests try to buy the same ticket at the same time:

1. The first one locks the row.
2. The second one waits on that lock.
3. The first one sets `user_id` and commits, which releases the lock.
4. The second one now reads the updated row, sees it has an owner and answers `409`.

This works under PostgreSQL's default isolation level (`READ COMMITTED`), so it needs no retries, no special isolation level and no application-level locking. The lock is per ticket, so purchases of different tickets do not block each other.

The refund takes the same lock. Otherwise a duplicated refund could overwrite a purchase made in between and leave that buyer without the ticket.

### Trying the race condition

With the API running and ticket 1 available, send 20 purchases for it at once:

```bash
seq 20 | xargs -P 20 -I{} curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST http://127.0.0.1:8000/tickets/buy/1 \
  -H "Content-Type: application/json" -d '{"user_id": 1}' | sort | uniq -c
```

Exactly one request gets `200` and the other nineteen get `409`.

### A flat, small code base

- `models.py`: the SQLAlchemy models (`User`, `Ticket`) and the request body (`TicketRequest`).
- `database.py`: loads `.env` and creates the engine.
- `seed.py`: creates and populates the tables.
- `main.py`: the three endpoints.

Each endpoint opens its own session with `with Session(engine)`. Leaving that block closes the session, so a request that ends in an error rolls back and releases its lock right away.

### Simplifications

- There is a single implicit event, so there is no `Event` model.
- There is no authentication: the `user_id` in the request body says who is buying or refunding.
- Tables are created by the seed script instead of migrations.

