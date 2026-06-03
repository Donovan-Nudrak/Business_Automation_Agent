import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.services.event_service import EventService, get_event_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _service(db: Session = Depends(get_db)) -> EventService:
    return get_event_service(db)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    event_service: EventService = Depends(_service),
) -> dict[str, str]:
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )

    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="STRIPE_WEBHOOK_SECRET is not configured",
        )

    try:
        stripe_event = stripe.Webhook.construct_event(
            payload,
            signature,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe signature",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe payload",
        ) from exc

    stripe_event_dict = (
        stripe_event.to_dict()
        if hasattr(stripe_event, "to_dict")
        else dict(stripe_event)
    )

    result = event_service.ingest_stripe_webhook(stripe_event_dict)

    if result.already_processed:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "already_processed",
                "event_id": str(result.event.id),
            },
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": result.event.status,
            "event_id": str(result.event.id),
        },
    )
