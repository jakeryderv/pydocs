"""pydocs - Interactive Python package documentation explorer."""

__version__ = "0.1.0"

from .inspector import inspect_path, resolve_dotted_path
from .models import (
    ClassInfo,
    InspectionResult,
    MemberInfo,
    MemberKind,
    ModuleInfo,
    SignatureInfo,
    SourceInfo,
)

__all__ = [
    "__version__",
    "inspect_path",
    "resolve_dotted_path",
    "ClassInfo",
    "InspectionResult",
    "MemberInfo",
    "MemberKind",
    "ModuleInfo",
    "SignatureInfo",
    "SourceInfo",
]
