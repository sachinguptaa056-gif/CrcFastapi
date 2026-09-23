from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    AvailabilityResponse,
    Event,
    EventCreate,
    EventRead,
    EventStatus,
    EventUpdate,
    MessageResponse,
    Reservation,
    ReservationCreate,
    ReservationRead,
)

router = APIRouter(prefix="/events", tags=["Events"])


@router.post(
    "",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new event",
    description="Registers a new event with title, venue, capacity (>0), organizer, and status (defaults to Open).",
)
def create_event(
    event_data: EventCreate,
    session: Session = Depends(get_session),
) -> Event:
    event = Event.model_validate(event_data)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@router.get(
    "",
    response_model=List[EventRead],
    summary="List all events",
    description="Fetches a list of all events in the system.",
)
def list_events(
    session: Session = Depends(get_session),
) -> List[Event]:
    events = session.exec(select(Event)).all()
    return list(events)


@router.get(
    "/{event_id}",
    response_model=EventRead,
    summary="Get event by ID",
    description="Retrieves detailed information for a specific event by its ID.",
)
def get_event(
    event_id: int,
    session: Session = Depends(get_session),
) -> Event:
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found.",
        )
    return event


@router.put(
    "/{event_id}",
    response_model=EventRead,
    summary="Update an event",
    description="Updates event properties (title, venue, capacity, organizer, status).",
)
def update_event(
    event_id: int,
    event_update: EventUpdate,
    session: Session = Depends(get_session),
) -> Event:
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found.",
        )

    update_dict = event_update.model_dump(exclude_unset=True)

    # If reducing capacity, verify it does not fall below existing confirmed bookings
    if "capacity" in update_dict and update_dict["capacity"] is not None:
        new_capacity = update_dict["capacity"]
        booked_count = session.exec(
            select(func.count(Reservation.id)).where(Reservation.event_id == event_id)
        ).one()
        if new_capacity < booked_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot reduce capacity to {new_capacity}. "
                    f"There are already {booked_count} confirmed reservations."
                ),
            )

    for field, value in update_dict.items():
        setattr(event, field, value)

    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@router.delete(
    "/{event_id}",
    response_model=MessageResponse,
    summary="Delete an event",
    description="Deletes an event along with any reservations associated with it.",
)
def delete_event(
    event_id: int,
    session: Session = Depends(get_session),
) -> MessageResponse:
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found.",
        )

    # Delete all associated reservations first
    associated_reservations = session.exec(
        select(Reservation).where(Reservation.event_id == event_id)
    ).all()
    for res in associated_reservations:
        session.delete(res)

    session.delete(event)
    session.commit()
    return MessageResponse(
        message=f"Event {event_id} and all associated reservations deleted successfully."
    )


@router.post(
    "/{event_id}/reserve",
    response_model=ReservationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a reservation for an event",
    description=(
        "Reserves a seat for a student in an event. Validates event existence, "
        "checks that the event is Open, and enforces maximum capacity constraints."
    ),
)
def reserve_seat(
    event_id: int,
    reservation_data: ReservationCreate,
    session: Session = Depends(get_session),
) -> Reservation:
    # 1. Verify that the event exists
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found.",
        )

    # 2. Verify that the event is Open
    if event.status != EventStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reserve seat: This event is currently Closed for registrations.",
        )

    # 3. Check number of existing reservations and prevent exceeding capacity
    booked_count = session.exec(
        select(func.count(Reservation.id)).where(Reservation.event_id == event_id)
    ).one()

    if booked_count >= event.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reserve seat: Event has reached its maximum capacity of {event.capacity}.",
        )

    # 4. Prevent duplicate reservation by same roll number or email for the same event
    existing_reservation = session.exec(
        select(Reservation).where(
            Reservation.event_id == event_id,
            (Reservation.roll_number == reservation_data.roll_number)
            | (Reservation.email == reservation_data.email),
        )
    ).first()
    if existing_reservation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Student with roll number '{reservation_data.roll_number}' or email "
                f"'{reservation_data.email}' already has a reservation for this event."
            ),
        )

    # 5. Create reservation
    reservation = Reservation(
        event_id=event_id,
        student_name=reservation_data.student_name,
        roll_number=reservation_data.roll_number,
        email=reservation_data.email,
    )
    session.add(reservation)
    session.commit()
    session.refresh(reservation)
    return reservation


@router.get(
    "/{event_id}/reservations",
    response_model=List[ReservationRead],
    summary="Get all reservations for an event",
    description="Returns a list of all student reservations made for a given event.",
)
def list_event_reservations(
    event_id: int,
    session: Session = Depends(get_session),
) -> List[Reservation]:
    # Verify event exists
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found.",
        )

    reservations = session.exec(
        select(Reservation).where(Reservation.event_id == event_id)
    ).all()
    return list(reservations)


@router.get(
    "/{event_id}/availability",
    response_model=AvailabilityResponse,
    summary="Get seat availability for an event",
    description="Calculates total capacity, number of booked seats, and remaining available seats.",
)
def get_event_availability(
    event_id: int,
    session: Session = Depends(get_session),
) -> AvailabilityResponse:
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found.",
        )

    booked_count = session.exec(
        select(func.count(Reservation.id)).where(Reservation.event_id == event_id)
    ).one()

    remaining_seats = max(0, event.capacity - booked_count)
    return AvailabilityResponse(
        capacity=event.capacity,
        booked=booked_count,
        remaining=remaining_seats,
    )
