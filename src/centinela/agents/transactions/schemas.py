from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class OriginAccount(BaseModel):
    id: str
    age_days: int = Field(ge=0)
    avg_monthly_amount: float = Field(gt=0)
    country: str = Field(min_length=2, max_length=2)


class DestinationAccount(BaseModel):
    id: str
    bank: str
    is_new_beneficiary: bool = False
    country: str = Field(min_length=2, max_length=2)


class Device(BaseModel):
    id: str
    is_new_device: bool = False
    os: str
    ip_country: str = Field(min_length=2, max_length=2)
    vpn: bool = False


class Geo(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    distance_from_home_km: float = Field(ge=0)


class Behavior(BaseModel):
    tx_last_hour: int = Field(ge=0)
    tx_last_24h: int = Field(ge=0)
    failed_logins_24h: int = Field(ge=0)
    session_seconds: int = Field(ge=0)


class CustomerProfile(BaseModel):
    segment: str
    risk_tier: Literal["bajo", "medio", "alto"]


class TransactionInput(BaseModel):
    transaction_id: str
    timestamp: datetime
    amount: float = Field(gt=0)
    currency: Literal["CLP"] = "CLP"
    channel: str
    type: str
    origin_account: OriginAccount
    destination_account: DestinationAccount
    device: Device
    geo: Geo
    behavior: Behavior
    customer_profile: CustomerProfile


class TransactionReasoning(BaseModel):
    score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    reasons: list[str]
    explanation_customer: str
    explanation_analyst: str
    recommended_action: Literal["aprobar", "validacion_adicional", "bloquear"]

