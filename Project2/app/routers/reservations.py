from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.models import MessageResponse, Reservation

router = APIRouter(prefix="/reservations", tags=["Reservations"])


@router.delete(
    "/{reservation_id}",
    response_model=MessageResponse,
    summary="Cancel a reservation",
    description="Deletes an existing student reservation by its ID.",
)
def cancel_reservation(
    reservation_id: int,
    session: Session = Depends(get_session),
) -> MessageResponse:
    reservation = session.get(Reservation, reservation_id)
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with ID {reservation_id} not found.",
        )

    session.delete(reservation)
    session.commit()
    return MessageResponse(
        message=f"Reservation {reservation_id} successfully cancelled."
    )
