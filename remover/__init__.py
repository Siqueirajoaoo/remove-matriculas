"""Remove matrículas (registrations) de aeronaves em imagens."""

from .pipeline import RegistrationRemover, RemovalResult
from .patterns import is_registration

__all__ = ["RegistrationRemover", "RemovalResult", "is_registration"]
