"""Data models for pydocs introspection results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class MemberKind(Enum):
    """Classification of Python object types."""

    MODULE = auto()
    PACKAGE = auto()
    CLASS = auto()
    FUNCTION = auto()
    METHOD = auto()
    CLASSMETHOD = auto()
    STATICMETHOD = auto()
    PROPERTY = auto()
    CONSTANT = auto()
    VARIABLE = auto()
    BUILTIN = auto()
    DATA = auto()


class ParameterKind(Enum):
    """Parameter passing convention (maps to inspect.Parameter.kind)."""

    POSITIONAL_ONLY = auto()
    POSITIONAL_OR_KEYWORD = auto()
    VAR_POSITIONAL = auto()
    KEYWORD_ONLY = auto()
    VAR_KEYWORD = auto()


@dataclass
class ParameterInfo:
    """Represents a function/method parameter."""

    name: str
    kind: ParameterKind
    annotation: Optional[str] = None
    default: Optional[str] = None
    has_default: bool = False


@dataclass
class SignatureInfo:
    """Function/method signature information."""

    parameters: list[ParameterInfo] = field(default_factory=list)
    return_annotation: Optional[str] = None
    raw_signature: Optional[str] = None


@dataclass
class SourceInfo:
    """Source code information."""

    source: Optional[str] = None
    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    is_builtin: bool = False


@dataclass
class MemberInfo:
    """Base information for any Python object member."""

    name: str
    kind: MemberKind
    qualified_name: str
    docstring: Optional[str] = None
    signature: Optional[SignatureInfo] = None
    source: Optional[SourceInfo] = None
    is_private: bool = False
    is_dunder: bool = False
    defining_module: Optional[str] = None
    is_imported: bool = False
    value_repr: Optional[str] = None


@dataclass
class ClassInfo(MemberInfo):
    """Extended information for classes."""

    bases: list[str] = field(default_factory=list)
    mro: list[str] = field(default_factory=list)
    methods: list[MemberInfo] = field(default_factory=list)
    class_methods: list[MemberInfo] = field(default_factory=list)
    static_methods: list[MemberInfo] = field(default_factory=list)
    properties: list[MemberInfo] = field(default_factory=list)
    class_variables: list[MemberInfo] = field(default_factory=list)
    is_abstract: bool = False


@dataclass
class ModuleInfo(MemberInfo):
    """Extended information for modules/packages."""

    is_package: bool = False
    file_path: Optional[str] = None
    submodules: list[str] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[MemberInfo] = field(default_factory=list)
    constants: list[MemberInfo] = field(default_factory=list)
    variables: list[MemberInfo] = field(default_factory=list)


@dataclass
class InspectionResult:
    """Top-level result from inspecting any path."""

    target: str
    resolved_path: str
    kind: MemberKind
    info: MemberInfo | ClassInfo | ModuleInfo
    error: Optional[str] = None
