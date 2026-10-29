class GymError(Exception):
    """Base class for all Gym-related errors."""
    pass
class NotFoundError(GymError):
    """Raised when a  we cant find a member or class."""
    pass
class RuleViolationError(GymError):
    """Raised when a rule violation occurs."""
    pass