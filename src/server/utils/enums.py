from enums import Enum, auto

# ========= client alerts, and statuss==========

class AlertSeverity(str,Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNDEFINED = "undefined"

class AlertStatus(str,Enum):
    UNRESOLVED = "unresolved"
    UNDER_REVIEW = "acknowledged"
    RESOLVED = "resolved"

class ChangeStatus(str,Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    
class Status(str,Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


 