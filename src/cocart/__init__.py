"""CoCart Python SDK — Official SDK for the CoCart REST API."""

# Core
from cocart.cocart import CoCart
from cocart.response import Response
from cocart.paginator import Paginator
from cocart.jwt_manager import JwtManager
from cocart.session_manager import SessionManager

# Endpoints
from cocart.endpoints.endpoint import Endpoint
from cocart.endpoints.account import Account
from cocart.endpoints.cart import Cart
from cocart.endpoints.products import Products
from cocart.endpoints.store import Store
from cocart.endpoints.sessions import Sessions

# Exceptions
from cocart.exceptions.cocart_exception import CoCartException
from cocart.exceptions.authentication_exception import AuthenticationException
from cocart.exceptions.two_factor_required_exception import TwoFactorRequiredException
from cocart.exceptions.validation_exception import ValidationException
from cocart.exceptions.version_exception import VersionException

# Utilities
from cocart.currency_formatter import CurrencyFormatter
from cocart.timezone import TimezoneHelper
from cocart.validation import validate_product_id, validate_quantity, validate_email

# Storage
from cocart.storage.storage import StorageInterface
from cocart.storage.memory_storage import MemoryStorage
from cocart.storage.file_storage import FileStorage

# HTTP
from cocart.http.adapter import HttpAdapter
from cocart.http.http_response import HttpResponse
from cocart.http.requests_adapter import RequestsAdapter

__version__ = "1.0.0"

__all__ = [
    # Core
    "CoCart",
    "Response",
    "Paginator",
    "JwtManager",
    "SessionManager",
    # Endpoints
    "Endpoint",
    "Account",
    "Cart",
    "Products",
    "Store",
    "Sessions",
    # Exceptions
    "CoCartException",
    "AuthenticationException",
    "TwoFactorRequiredException",
    "ValidationException",
    "VersionException",
    # Utilities
    "CurrencyFormatter",
    "TimezoneHelper",
    "validate_product_id",
    "validate_quantity",
    "validate_email",
    # Storage
    "StorageInterface",
    "MemoryStorage",
    "FileStorage",
    # HTTP
    "HttpAdapter",
    "HttpResponse",
    "RequestsAdapter",
]
