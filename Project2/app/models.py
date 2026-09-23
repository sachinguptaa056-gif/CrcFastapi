from enum import Enum
from typing import List, Optional
from pydantic import EmailStr, field_validator
from sqlmodel import Field, Relationship, SQLModel


class EventStatus(str, Enum):
    """Status indicating whether reservations are accepted."""
    OPEN = "Open"
    CLOSED = "Closed"


class EventBase(SQLModel):
    """Shared attributes for Event models."""
    title: str = Field(min_length=1, max_length=200, description="Title/name of the event")
    venue: str = Field(min_length=1, max_length=200, description="Location/venue of the event")
    capacity: int = Field(gt=0, description="Maximum number of attendees allowed (must be > 0)")
    organizer: str = Field(min_length=1, max_length=150, description="Event organizer name")
    status: EventStatus = Field(default=EventStatus.OPEN, description="Event status: Open or Closed")

    @field_validator("title", "venue", "organizer")
    @classmethod
    def validate_non_empty_strings(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Field must not be empty or contain only whitespace.")
        return value.strip()


class Event(EventBase, table=True):
    """Database table model for events."""
    __tablename__ = "events"

    id: Optional[int] = Field(default=None, primary_key=True)
    reservations: List["Reservation"] = Relationship(
        back_populates="event",
        cascade_delete=True,
    )


class EventCreate(EventBase):
    """Request schema for creating a new event."""
    pass


class EventUpdate(SQLModel):
    """Request schema for updating an existing event."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    venue: Optional[str] = Field(default=None, min_length=1, max_length=200)
    capacity: Optional[int] = Field(default=None, gt=0)
    organizer: Optional[str] = Field(default=None, min_length=1, max_length=150)
    status: Optional[EventStatus] = None

    @field_validator("title", "venue", "organizer")
    @classmethod
    def validate_optional_non_empty(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            if not value.strip():
                raise ValueError("Field cannot be empty or contain only whitespace.")
            return value.strip()
        return value


class EventRead(EventBase):
    """Response schema returning event details."""
    id: int


class ReservationBase(SQLModel):
    """Shared attributes for Reservation models."""
    student_name: str = Field(min_length=1, max_length=120, description="Full name of the participant")
    roll_number: str = Field(min_length=1, max_length=60, description="Participant's roll / student ID")
    email: EmailStr = Field(description="Valid participant email address")

    @field_validator("student_name", "roll_number")
    @classmethod
    def validate_non_empty_reservation_fields(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Field must not be empty or contain only whitespace.")
        return value.strip()


class Reservation(ReservationBase, table=True):
    """Database table model for student reservations."""
    __tablename__ = "reservations"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="events.id", index=True, description="Referenced Event ID")
    event: Optional[Event] = Relationship(back_populates="reservations")


class ReservationCreate(ReservationBase):
    """Request schema for creating a reservation (event_id passed in URL path)."""
    pass


class ReservationRead(ReservationBase):
    """Response schema returning reservation details."""
    id: int
    event_id: int


class AvailabilityResponse(SQLModel):
    """Response schema for seat availability of an event."""
    capacity: int
    booked: int
    remaining: int


class MessageResponse(SQLModel):
    """Standard message response schema for operations like delete."""
    message: str
