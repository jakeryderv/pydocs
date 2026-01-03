"""Core introspection engine for pydocs."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Any, Optional

from .models import (
    ClassInfo,
    InspectionResult,
    MemberInfo,
    MemberKind,
    ModuleInfo,
    ParameterInfo,
    ParameterKind,
    SignatureInfo,
    SourceInfo,
)


def resolve_dotted_path(path: str) -> tuple[Any, str, list[str]]:
    """
    Resolve a dotted path like 'urllib.parse.urlparse' to an object.

    Returns:
        Tuple of (object, module_path, attribute_chain)

    Raises:
        ImportError: If the path cannot be resolved
    """
    parts = path.split(".")

    # Try progressively shorter module paths
    for i in range(len(parts), 0, -1):
        module_path = ".".join(parts[:i])
        try:
            obj = importlib.import_module(module_path)
            # Traverse remaining attributes
            for attr in parts[i:]:
                obj = getattr(obj, attr)
            return obj, module_path, parts[i:]
        except ImportError:
            continue
        except AttributeError:
            continue

    raise ImportError(f"Cannot resolve path: {path}")


def classify_object(obj: Any, name: str = "") -> MemberKind:
    """Determine the MemberKind of a Python object."""
    if inspect.ismodule(obj):
        return MemberKind.PACKAGE if hasattr(obj, "__path__") else MemberKind.MODULE

    if inspect.isclass(obj):
        return MemberKind.CLASS

    if inspect.isbuiltin(obj):
        return MemberKind.BUILTIN

    if inspect.isfunction(obj):
        return MemberKind.FUNCTION

    if inspect.ismethod(obj):
        return MemberKind.METHOD

    if isinstance(obj, classmethod):
        return MemberKind.CLASSMETHOD

    if isinstance(obj, staticmethod):
        return MemberKind.STATICMETHOD

    if isinstance(obj, property):
        return MemberKind.PROPERTY

    # Heuristic for constants: UPPER_CASE and simple type
    if name and name.isupper() and isinstance(obj, (str, int, float, bool, type(None), bytes, tuple)):
        return MemberKind.CONSTANT

    return MemberKind.VARIABLE


def extract_signature(obj: Any) -> Optional[SignatureInfo]:
    """
    Extract signature from a callable.

    Handles built-ins gracefully (may have limited info).
    """
    try:
        sig = inspect.signature(obj)
    except (ValueError, TypeError):
        return None

    kind_map = {
        inspect.Parameter.POSITIONAL_ONLY: ParameterKind.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD: ParameterKind.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.VAR_POSITIONAL: ParameterKind.VAR_POSITIONAL,
        inspect.Parameter.KEYWORD_ONLY: ParameterKind.KEYWORD_ONLY,
        inspect.Parameter.VAR_KEYWORD: ParameterKind.VAR_KEYWORD,
    }

    params = []
    for param_name, param in sig.parameters.items():
        has_default = param.default is not inspect.Parameter.empty
        params.append(
            ParameterInfo(
                name=param_name,
                kind=kind_map[param.kind],
                annotation=_format_annotation(param.annotation),
                default=repr(param.default) if has_default else None,
                has_default=has_default,
            )
        )

    return SignatureInfo(
        parameters=params,
        return_annotation=_format_annotation(sig.return_annotation),
        raw_signature=str(sig),
    )


def _format_annotation(ann: Any) -> Optional[str]:
    """Convert annotation to readable string."""
    if ann is inspect.Parameter.empty or ann is inspect.Signature.empty:
        return None
    return inspect.formatannotation(ann)


def extract_source(obj: Any) -> SourceInfo:
    """
    Extract source code, handling edge cases gracefully.
    """
    try:
        source = inspect.getsource(obj)
        source_file = inspect.getsourcefile(obj)
        lines, start_line = inspect.getsourcelines(obj)
        return SourceInfo(
            source=source,
            file_path=source_file,
            start_line=start_line,
            end_line=start_line + len(lines) - 1,
            is_builtin=False,
        )
    except (OSError, TypeError):
        # Built-in or C extension
        try:
            file_path = inspect.getfile(obj)
        except TypeError:
            file_path = None
        return SourceInfo(is_builtin=True, file_path=file_path)


def inspect_module(
    module: Any,
    include_private: bool = False,
    include_imported: bool = False,
) -> ModuleInfo:
    """
    Fully inspect a module/package.
    """
    module_name = module.__name__

    # Discover submodules for packages
    submodules: list[str] = []
    if hasattr(module, "__path__"):
        try:
            for _, name, _ in pkgutil.iter_modules(module.__path__):
                submodules.append(name)
        except Exception:
            pass

    classes: list[ClassInfo] = []
    functions: list[MemberInfo] = []
    constants: list[MemberInfo] = []
    variables: list[MemberInfo] = []

    for name, obj in inspect.getmembers(module):
        # Filter private
        if not include_private and name.startswith("_"):
            continue

        # Skip modules (submodules are handled separately)
        if inspect.ismodule(obj):
            continue

        # Check if imported from elsewhere
        obj_module = getattr(obj, "__module__", None)
        is_imported = obj_module is not None and obj_module != module_name

        # Skip imported unless requested
        if not include_imported and is_imported:
            continue

        kind = classify_object(obj, name)

        if kind == MemberKind.CLASS:
            classes.append(inspect_class(obj, f"{module_name}.{name}", include_private))
        elif kind in (MemberKind.FUNCTION, MemberKind.BUILTIN):
            functions.append(_create_member_info(obj, name, kind, module_name, is_imported))
        elif kind == MemberKind.CONSTANT:
            info = _create_member_info(obj, name, kind, module_name, is_imported)
            info.value_repr = _safe_repr(obj)
            constants.append(info)
        elif kind == MemberKind.VARIABLE:
            info = _create_member_info(obj, name, kind, module_name, is_imported)
            info.value_repr = _safe_repr(obj)
            variables.append(info)

    return ModuleInfo(
        name=module_name.split(".")[-1],
        kind=MemberKind.PACKAGE if submodules else MemberKind.MODULE,
        qualified_name=module_name,
        docstring=inspect.getdoc(module),
        is_package=bool(submodules) or hasattr(module, "__path__"),
        file_path=getattr(module, "__file__", None),
        submodules=sorted(submodules),
        classes=sorted(classes, key=lambda c: c.name),
        functions=sorted(functions, key=lambda f: f.name),
        constants=sorted(constants, key=lambda c: c.name),
        variables=sorted(variables, key=lambda v: v.name),
    )


def inspect_class(
    cls: type,
    qualified_name: str,
    include_private: bool = False,
) -> ClassInfo:
    """
    Fully inspect a class.
    """
    methods: list[MemberInfo] = []
    class_methods: list[MemberInfo] = []
    static_methods: list[MemberInfo] = []
    properties: list[MemberInfo] = []
    class_variables: list[MemberInfo] = []

    for attr in inspect.classify_class_attrs(cls):
        # Filter private
        if not include_private and attr.name.startswith("_"):
            continue

        # Skip inherited if not from this class
        is_inherited = attr.defining_class != cls

        member_kind_map = {
            "method": MemberKind.METHOD,
            "class method": MemberKind.CLASSMETHOD,
            "static method": MemberKind.STATICMETHOD,
            "property": MemberKind.PROPERTY,
            "data": MemberKind.DATA,
        }
        member_kind = member_kind_map.get(attr.kind, MemberKind.VARIABLE)

        info = _create_member_info(
            attr.object,
            attr.name,
            member_kind,
            qualified_name,
            is_inherited,
        )

        if attr.kind == "method":
            methods.append(info)
        elif attr.kind == "class method":
            class_methods.append(info)
        elif attr.kind == "static method":
            static_methods.append(info)
        elif attr.kind == "property":
            properties.append(info)
        elif attr.kind == "data":
            info.value_repr = _safe_repr(attr.object)
            class_variables.append(info)

    return ClassInfo(
        name=cls.__name__,
        kind=MemberKind.CLASS,
        qualified_name=qualified_name,
        docstring=inspect.getdoc(cls),
        signature=extract_signature(cls),
        bases=[b.__name__ for b in cls.__bases__ if b is not object],
        mro=[c.__name__ for c in cls.__mro__[1:-1]],  # Skip self and object
        methods=sorted(methods, key=lambda m: m.name),
        class_methods=sorted(class_methods, key=lambda m: m.name),
        static_methods=sorted(static_methods, key=lambda m: m.name),
        properties=sorted(properties, key=lambda p: p.name),
        class_variables=sorted(class_variables, key=lambda v: v.name),
        is_abstract=inspect.isabstract(cls),
    )


def _create_member_info(
    obj: Any,
    name: str,
    kind: MemberKind,
    parent_path: str,
    is_imported: bool,
) -> MemberInfo:
    """Helper to create MemberInfo with common fields."""
    return MemberInfo(
        name=name,
        kind=kind,
        qualified_name=f"{parent_path}.{name}",
        docstring=inspect.getdoc(obj),
        signature=extract_signature(obj) if callable(obj) else None,
        is_private=name.startswith("_"),
        is_dunder=name.startswith("__") and name.endswith("__"),
        is_imported=is_imported,
    )


def _safe_repr(obj: Any, max_len: int = 80) -> str:
    """Get a safe string representation of an object."""
    try:
        r = repr(obj)
        if len(r) > max_len:
            r = r[: max_len - 3] + "..."
        return r
    except Exception:
        return f"<{type(obj).__name__}>"


def inspect_path(
    path: str,
    include_private: bool = False,
    include_imported: bool = False,
) -> InspectionResult:
    """
    Main entry point: inspect any dotted path.
    """
    try:
        obj, module_path, attrs = resolve_dotted_path(path)
        kind = classify_object(obj, path.split(".")[-1] if "." in path else path)

        if kind in (MemberKind.MODULE, MemberKind.PACKAGE):
            info = inspect_module(obj, include_private, include_imported)
        elif kind == MemberKind.CLASS:
            info = inspect_class(obj, path, include_private)
        else:
            parent_path = ".".join(path.split(".")[:-1]) if "." in path else ""
            info = _create_member_info(
                obj,
                path.split(".")[-1],
                kind,
                parent_path,
                False,
            )
            info.source = extract_source(obj)

        return InspectionResult(
            target=path,
            resolved_path=path,
            kind=kind,
            info=info,
        )
    except Exception as e:
        return InspectionResult(
            target=path,
            resolved_path=path,
            kind=MemberKind.VARIABLE,
            info=MemberInfo(
                name=path,
                kind=MemberKind.VARIABLE,
                qualified_name=path,
            ),
            error=str(e),
        )
