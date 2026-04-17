from pydantic import BaseModel, ConfigDict


# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class SignupRequest(BaseModel):
    username: str
    password: str
    password2: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str


# ── Trips ────────────────────────────────────────────────────────────────────

class SegmentInput(BaseModel):
    start: str
    end: str
    mode: str

class TripLogRequest(BaseModel):
    date: str
    start: str
    end: str
    mode: str
    car: str = ""
    notes: str = ""
    round_trip: bool = False
    segments: list[SegmentInput] | None = None

class SegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    position: int
    start_loc: str
    end_loc: str
    mode: str
    miles: float

class TripResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: str
    start_loc: str
    end_loc: str
    mode: str
    car_name: str | None
    miles: float
    co2_kg: float
    notes: str | None
    segments: list[SegmentResponse] = []

class SummaryModeRow(BaseModel):
    mode: str
    miles: float
    trips: int

class SummaryCarRow(BaseModel):
    car_name: str
    miles: float
    co2_kg: float

class WeekData(BaseModel):
    week: str
    miles: float
    trips: int
    by_mode: dict[str, float]

class SummaryResponse(BaseModel):
    total_miles: float
    total_co2_kg: float
    total_trips: int
    top_mode: str
    by_mode: list[SummaryModeRow]
    by_car: list[SummaryCarRow]
    over_time: list[WeekData]


# ── Cars ─────────────────────────────────────────────────────────────────────

class CarCreateRequest(BaseModel):
    name: str
    mpg: float
    fuel_type: str = "gasoline"

class CarUpdateRequest(BaseModel):
    name: str | None = None
    mpg: float | None = None
    fuel_type: str | None = None

class CarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    mpg: float
    fuel_type: str
    is_default: bool

class ReorderRequest(BaseModel):
    ids: list[int]


# ── Addresses ────────────────────────────────────────────────────────────────

class AddressCreateRequest(BaseModel):
    label: str
    address: str

class AddressUpdateRequest(BaseModel):
    label: str | None = None
    address: str | None = None

class AddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    label: str
    address: str
