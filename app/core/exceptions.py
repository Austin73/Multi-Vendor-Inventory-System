class InventoryException(Exception):
    """Base exception for inventory system."""
    pass


class NotFoundError(InventoryException):
    def __init__(self, resource: str, identifier):
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} with id '{identifier}' not found.")


class DuplicateError(InventoryException):
    def __init__(self, resource: str, field: str, value):
        self.resource = resource
        self.field = field
        self.value = value
        super().__init__(f"{resource} with {field} '{value}' already exists.")


class BusinessRuleError(InventoryException):
    """Raised when a business rule is violated."""
    pass
