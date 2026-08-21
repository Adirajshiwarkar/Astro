import uuid
from datetime import date, datetime, time
from typing import Any, Dict

class BirthData:
    def __init__(
        self,
        id: uuid.UUID = None,
        profile_id: uuid.UUID = None,
        date_of_birth: date = None,
        birth_time: time = None,
        birth_place: str = "",
        latitude: float = 0.0,
        longitude: float = 0.0,
        timezone: str = "",
        dst_handling: bool = False,
        timezone_source: str = "",
        coordinate_source: str = "",
        normalized_birth_datetime: datetime = None,
        calculation_metadata: dict = None,
        created_at: datetime = None,
        updated_at: datetime = None,
    ):
        self.id = id or uuid.uuid4()
        self.profile_id = profile_id
        self.date_of_birth = date_of_birth
        self.birth_time = birth_time
        self.birth_place = birth_place
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone
        self.dst_handling = dst_handling
        self.timezone_source = timezone_source
        self.coordinate_source = coordinate_source
        self.normalized_birth_datetime = normalized_birth_datetime
        self.calculation_metadata = calculation_metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": str(self.id),
            "id": str(self.id),
            "profile_id": str(self.profile_id) if self.profile_id else None,
            "date_of_birth": self.date_of_birth.isoformat() if isinstance(self.date_of_birth, date) else self.date_of_birth,
            "birth_time": self.birth_time.isoformat() if isinstance(self.birth_time, time) else self.birth_time,
            "birth_place": self.birth_place,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone,
            "dst_handling": self.dst_handling,
            "timezone_source": self.timezone_source,
            "coordinate_source": self.coordinate_source,
            "normalized_birth_datetime": self.normalized_birth_datetime.isoformat() if isinstance(self.normalized_birth_datetime, datetime) else self.normalized_birth_datetime,
            "calculation_metadata": self.calculation_metadata,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BirthData":
        if not data:
            return None
        dob = data.get("date_of_birth")
        if isinstance(dob, str):
            dob = date.fromisoformat(dob)
        bt = data.get("birth_time")
        if isinstance(bt, str):
            bt = time.fromisoformat(bt)
        nbd = data.get("normalized_birth_datetime")
        if isinstance(nbd, str):
            nbd = datetime.fromisoformat(nbd)
        ca = data.get("created_at")
        if isinstance(ca, str):
            ca = datetime.fromisoformat(ca)
        ua = data.get("updated_at")
        if isinstance(ua, str):
            ua = datetime.fromisoformat(ua)
        
        bd_id = data.get("_id") or data.get("id")
        return cls(
            id=uuid.UUID(bd_id) if isinstance(bd_id, str) else bd_id,
            profile_id=uuid.UUID(data["profile_id"]) if isinstance(data.get("profile_id"), str) else data.get("profile_id"),
            date_of_birth=dob,
            birth_time=bt,
            birth_place=data.get("birth_place", ""),
            latitude=data.get("latitude", 0.0),
            longitude=data.get("longitude", 0.0),
            timezone=data.get("timezone", ""),
            dst_handling=data.get("dst_handling", False),
            timezone_source=data.get("timezone_source", ""),
            coordinate_source=data.get("coordinate_source", ""),
            normalized_birth_datetime=nbd,
            calculation_metadata=data.get("calculation_metadata"),
            created_at=ca,
            updated_at=ua,
        )

class UserProfile:
    def __init__(
        self,
        id: uuid.UUID = None,
        user_id: uuid.UUID = None,
        first_name: str = None,
        last_name: str = None,
        current_location: str = None,
        created_at: datetime = None,
        updated_at: datetime = None,
        birth_data: BirthData = None,
    ):
        self.id = id or uuid.uuid4()
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.current_location = current_location
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.birth_data = birth_data

    def to_dict(self, include_nested: bool = False) -> Dict[str, Any]:
        data = {
            "_id": str(self.id),
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "current_location": self.current_location,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }
        if include_nested:
            data["birth_data"] = self.birth_data.to_dict() if self.birth_data else None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        if not data or not isinstance(data, dict):
            return None
        ca = data.get("created_at")
        if isinstance(ca, str):
            ca = datetime.fromisoformat(ca)
        ua = data.get("updated_at")
        if isinstance(ua, str):
            ua = datetime.fromisoformat(ua)
        bd_data = data.get("birth_data")
        bd = BirthData.from_dict(bd_data) if bd_data else None
        
        p_id = data.get("_id") or data.get("id")
        return cls(
            id=uuid.UUID(p_id) if isinstance(p_id, str) else p_id,
            user_id=uuid.UUID(data["user_id"]) if isinstance(data.get("user_id"), str) else data.get("user_id"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            current_location=data.get("current_location"),
            created_at=ca,
            updated_at=ua,
            birth_data=bd,
        )

class User:
    def __init__(
        self,
        id: uuid.UUID = None,
        email: str = "",
        hashed_password: str = "",
        is_active: bool = True,
        created_at: datetime = None,
        updated_at: datetime = None,
        profile: UserProfile = None,
    ):
        self.id = id or uuid.uuid4()
        self.email = email
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.profile = profile

    def to_dict(self, include_nested: bool = False) -> Dict[str, Any]:
        data = {
            "_id": str(self.id),
            "id": str(self.id),
            "email": self.email,
            "hashed_password": self.hashed_password,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }
        if include_nested:
            data["profile"] = self.profile.to_dict(include_nested=True) if self.profile else None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        if not data or not isinstance(data, dict):
            return None
        ca = data.get("created_at")
        if isinstance(ca, str):
            ca = datetime.fromisoformat(ca)
        ua = data.get("updated_at")
        if isinstance(ua, str):
            ua = datetime.fromisoformat(ua)
        prof_data = data.get("profile")
        prof = UserProfile.from_dict(prof_data) if prof_data else None
        
        user_id = data.get("_id") or data.get("id")
        return cls(
            id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            email=data.get("email", ""),
            hashed_password=data.get("hashed_password", ""),
            is_active=data.get("is_active", True),
            created_at=ca,
            updated_at=ua,
            profile=prof,
        )
