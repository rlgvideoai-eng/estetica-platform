"""Schemas package - Pydantic models for API."""
from .service import ServiceCreate, ServiceUpdate, ServiceResponse
from .professional import ProfessionalCreate, ProfessionalUpdate, ProfessionalResponse
from .availability import AvailabilityQuery, AvailabilitySlot, AvailabilityResponse
from .booking import BookingCreate, BookingUpdate, BookingResponse, BookingListResponse
from .client import ClientCreate, ClientResponse

__all__ = [
    "ServiceCreate",
    "ServiceUpdate",
    "ServiceResponse",
    "ProfessionalCreate",
    "ProfessionalUpdate",
    "ProfessionalResponse",
    "AvailabilityQuery",
    "AvailabilitySlot",
    "AvailabilityResponse",
    "BookingCreate",
    "BookingUpdate",
    "BookingResponse",
    "BookingListResponse",
    "ClientCreate",
    "ClientResponse",
]