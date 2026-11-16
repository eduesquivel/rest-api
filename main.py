from fastapi import FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import engine
from models import Ticket, TicketRequest, User

app = FastAPI()


@app.get("/tickets")
def list_available_tickets():
    with Session(engine) as session:
        ticket_ids = session.scalars(
            select(Ticket.id).where(Ticket.user_id.is_(None)).order_by(Ticket.id)
        ).all()
    return [{"id": ticket_id} for ticket_id in ticket_ids]


@app.post("/tickets/buy/{ticket_id}")
def buy_ticket(ticket_id: int, body: TicketRequest):
    with Session(engine) as session:
        if session.get(User, body.user_id) is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # FOR UPDATE: una petición concurrente sobre el mismo ticket espera al
        # commit de esta y luego lee la fila ya actualizada.
        ticket = session.scalars(
            select(Ticket).where(Ticket.id == ticket_id).with_for_update()
        ).one_or_none()
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        if ticket.user_id is not None:
            raise HTTPException(status_code=409, detail="Ticket ya vendido")

        ticket.user_id = body.user_id
        session.commit()
    return {"id": ticket_id, "user_id": body.user_id}


@app.post("/tickets/refund/{ticket_id}")
def refund_ticket(ticket_id: int, body: TicketRequest):
    with Session(engine) as session:
        ticket = session.scalars(
            select(Ticket).where(Ticket.id == ticket_id).with_for_update()
        ).one_or_none()
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        if ticket.user_id is None:
            raise HTTPException(status_code=409, detail="El ticket no está vendido")
        if ticket.user_id != body.user_id:
            raise HTTPException(status_code=403, detail="El ticket pertenece a otro usuario")

        ticket.user_id = None
        session.commit()
    return {"id": ticket_id, "user_id": None}
