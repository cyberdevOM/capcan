from enums import Enum, auto

# ========= client alerts, and statuss==========

class AlertSeverity(str,Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNDEFINED = "undefined"

class AlertStatus(str,Enum):
    UNRESOLVED = "unresolved"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"

class ChangeStatus(str,Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    
class Status(str,Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


