"""Rich-based terminal formatter for pydocs."""

from __future__ import annotations

import json as json_module
from dataclasses import asdict
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from ..models import (
    ClassInfo,
    InspectionResult,
    MemberInfo,
    MemberKind,
    ModuleInfo,
    ParameterKind,
    SignatureInfo,
)

# Color scheme for different member types
COLORS: dict[MemberKind, str] = {
    MemberKind.MODULE: "blue",
    MemberKind.PACKAGE: "blue bold",
    MemberKind.CLASS: "yellow",
    MemberKind.FUNCTION: "green",
    MemberKind.METHOD: "green",
    MemberKind.CLASSMETHOD: "green italic",
    MemberKind.STATICMETHOD: "green dim",
    MemberKind.PROPERTY: "magenta",
    MemberKind.CONSTANT: "cyan",
    MemberKind.VARIABLE: "white dim",
    MemberKind.BUILTIN: "red",
    MemberKind.DATA: "white dim",
}

# Icons/prefixes for different member types
ICONS: dict[MemberKind, str] = {
    MemberKind.PACKAGE: "pkg",
    MemberKind.MODULE: "mod",
    MemberKind.CLASS: "cls",
    MemberKind.FUNCTION: "def",
    MemberKind.METHOD: "def",
    MemberKind.CLASSMETHOD: "cls",
    MemberKind.STATICMETHOD: "sta",
    MemberKind.PROPERTY: "pro",
    MemberKind.CONSTANT: "const",
    MemberKind.VARIABLE: "var",
    MemberKind.BUILTIN: "blt",
    MemberKind.DATA: "dat",
}


class RichFormatter:
    """Rich-based formatter for inspection results."""

    def __init__(
        self,
        no_color: bool = False,
        max_depth: int = 2,
        show_imported: bool = False,
        show_private: bool = False,
    ) -> None:
        self.console = Console(no_color=no_color, force_terminal=not no_color)
        self.max_depth = max_depth
        self.show_imported = show_imported
        self.show_private = show_private

    def print_overview(self, result: InspectionResult) -> None:
        """Print full overview with tree structure."""
        if isinstance(result.info, ModuleInfo):
            self._print_module_overview(result.info)
        elif isinstance(result.info, ClassInfo):
            self._print_class_overview(result.info)
        else:
            self._print_member_overview(result.info)

    def _print_module_overview(self, info: ModuleInfo) -> None:
        """Render module/package as tree."""
        # Header with docstring
        title = f"[bold]{info.qualified_name}[/bold]"
        if info.is_package:
            title += " [dim](package)[/dim]"

        if info.docstring:
            # Truncate long docstrings for overview
            doc = info.docstring
            if len(doc) > 500:
                doc = doc[:500] + "..."
            self.console.print(
                Panel(
                    doc,
                    title=title,
                    subtitle=f"[dim]{info.file_path or 'built-in'}[/dim]",
                    border_style="blue",
                )
            )
        else:
            self.console.print(
                Panel(
                    "[dim]No documentation available[/dim]",
                    title=title,
                    subtitle=f"[dim]{info.file_path or 'built-in'}[/dim]",
                    border_style="blue",
                )
            )

        # Build tree
        icon = ICONS.get(info.kind, "")
        color = COLORS.get(info.kind, "white")
        tree = Tree(f"[{color}]{icon} {info.qualified_name}[/{color}]")

        # Submodules
        if info.submodules:
            submod_branch = tree.add("[blue bold]Submodules[/blue bold]")
            for name in info.submodules:
                submod_branch.add(f"[blue]{name}[/blue]")

        # Classes
        if info.classes:
            class_branch = tree.add("[yellow bold]Classes[/yellow bold]")
            for cls in info.classes:
                self._add_class_to_tree(class_branch, cls, depth=1)

        # Functions
        if info.functions:
            func_branch = tree.add("[green bold]Functions[/green bold]")
            for func in info.functions:
                sig = func.signature.raw_signature if func.signature else "()"
                imported_tag = " [dim](imported)[/dim]" if func.is_imported else ""
                func_branch.add(f"[green]{func.name}[/green][dim]{sig}[/dim]{imported_tag}")

        # Constants
        if info.constants:
            const_branch = tree.add("[cyan bold]Constants[/cyan bold]")
            for const in info.constants:
                value = f" = {const.value_repr}" if const.value_repr else ""
                const_branch.add(f"[cyan]{const.name}[/cyan][dim]{value}[/dim]")

        # Variables
        if info.variables:
            var_branch = tree.add("[white bold]Variables[/white bold]")
            for var in info.variables:
                value = f" = {var.value_repr}" if var.value_repr else ""
                var_branch.add(f"[dim]{var.name}{value}[/dim]")

        self.console.print(tree)

    def _add_class_to_tree(self, parent: Tree, cls: ClassInfo, depth: int) -> None:
        """Add class and its members to tree."""
        if depth > self.max_depth:
            bases = f"({', '.join(cls.bases)})" if cls.bases else ""
            parent.add(f"[yellow]{cls.name}[/yellow][dim]{bases}[/dim] ...")
            return

        bases = f"({', '.join(cls.bases)})" if cls.bases else ""
        abstract_tag = " [magenta italic]ABC[/magenta italic]" if cls.is_abstract else ""
        class_branch = parent.add(f"[yellow]{cls.name}[/yellow][dim]{bases}[/dim]{abstract_tag}")

        # Methods
        all_methods = cls.methods + cls.class_methods + cls.static_methods
        for method in all_methods:
            sig = method.signature.raw_signature if method.signature else "()"
            kind_prefix = ""
            if method.kind == MemberKind.CLASSMETHOD:
                kind_prefix = "[dim]@classmethod [/dim]"
            elif method.kind == MemberKind.STATICMETHOD:
                kind_prefix = "[dim]@staticmethod [/dim]"
            class_branch.add(f"{kind_prefix}[green]{method.name}[/green][dim]{sig}[/dim]")

        # Properties
        for prop in cls.properties:
            class_branch.add(f"[magenta]@{prop.name}[/magenta]")

    def _print_class_overview(self, info: ClassInfo) -> None:
        """Render class details."""
        # Header
        bases = f"({', '.join(info.bases)})" if info.bases else ""
        header = f"class [yellow bold]{info.name}[/yellow bold]{bases}"
        if info.is_abstract:
            header += " [magenta italic](abstract)[/magenta italic]"

        # Docstring panel
        if info.docstring:
            self.console.print(Panel(Markdown(info.docstring), title=header, border_style="yellow"))
        else:
            self.console.print(header)
            self.console.print()

        # Signature (for __init__)
        if info.signature:
            sig_text = self._format_signature(info.name, info.signature, is_class=True)
            self.console.print(Panel(sig_text, title="Constructor", border_style="dim"))

        # Methods table
        all_methods = info.methods + info.class_methods + info.static_methods
        if all_methods:
            table = Table(title="Methods", show_header=True, header_style="bold")
            table.add_column("Name", style="green")
            table.add_column("Type", style="dim")
            table.add_column("Signature", style="dim")

            for method in info.methods:
                sig = method.signature.raw_signature if method.signature else "()"
                table.add_row(method.name, "method", sig)
            for method in info.class_methods:
                sig = method.signature.raw_signature if method.signature else "()"
                table.add_row(method.name, "classmethod", sig)
            for method in info.static_methods:
                sig = method.signature.raw_signature if method.signature else "()"
                table.add_row(method.name, "staticmethod", sig)

            self.console.print(table)

        # Properties
        if info.properties:
            self.console.print("\n[bold]Properties:[/bold]")
            for prop in info.properties:
                doc = f" - {prop.docstring[:60]}..." if prop.docstring and len(prop.docstring) > 60 else ""
                if prop.docstring and len(prop.docstring) <= 60:
                    doc = f" - {prop.docstring}"
                self.console.print(f"  [magenta]@{prop.name}[/magenta]{doc}")

        # Class variables
        if info.class_variables:
            self.console.print("\n[bold]Class Variables:[/bold]")
            for var in info.class_variables:
                value = f" = {var.value_repr}" if var.value_repr else ""
                self.console.print(f"  [dim]{var.name}{value}[/dim]")

        # MRO
        if info.mro:
            self.console.print(f"\n[dim]MRO: {' -> '.join(info.mro)}[/dim]")

    def _print_member_overview(self, info: MemberInfo) -> None:
        """Render function/method details."""
        kind_name = info.kind.name.lower()
        color = COLORS.get(info.kind, "white")

        # Signature
        if info.signature:
            sig_text = self._format_signature(info.name, info.signature)
            self.console.print(Panel(sig_text, title=f"[{color}]{kind_name}[/{color}]", border_style=color))
        else:
            self.console.print(f"[{color}]{kind_name} {info.name}[/{color}]")

        # Docstring
        if info.docstring:
            self.console.print()
            self.console.print(Panel(Markdown(info.docstring), title="Documentation", border_style="dim"))

        # Source location
        if info.source and info.source.file_path:
            loc = info.source.file_path
            if info.source.start_line:
                loc += f":{info.source.start_line}"
            self.console.print(f"\n[dim]Defined in: {loc}[/dim]")
        elif info.source and info.source.is_builtin:
            self.console.print("\n[dim]Built-in (no source available)[/dim]")

    def _format_signature(
        self,
        name: str,
        sig: SignatureInfo,
        is_class: bool = False,
    ) -> Text:
        """Create rich-formatted signature."""
        text = Text()

        if is_class:
            text.append("class ", style="keyword")
        else:
            text.append("def ", style="keyword")

        text.append(name, style="bold")
        text.append("(")

        params = []
        for param in sig.parameters:
            param_text = Text()

            # Handle special parameter kinds
            if param.kind == ParameterKind.VAR_POSITIONAL:
                param_text.append("*", style="bold")
            elif param.kind == ParameterKind.VAR_KEYWORD:
                param_text.append("**", style="bold")

            param_text.append(param.name)

            if param.annotation:
                param_text.append(": ", style="dim")
                param_text.append(param.annotation, style="cyan")

            if param.has_default and param.default:
                param_text.append(" = ", style="dim")
                param_text.append(param.default, style="green dim")

            params.append(param_text)

        for i, p in enumerate(params):
            text.append_text(p)
            if i < len(params) - 1:
                text.append(", ")

        text.append(")")

        if sig.return_annotation:
            text.append(" -> ", style="dim")
            text.append(sig.return_annotation, style="cyan")

        return text

    def print_source(self, result: InspectionResult) -> None:
        """Print syntax-highlighted source code."""
        from ..inspector import extract_source, resolve_dotted_path

        # Get source info
        if hasattr(result.info, "source") and result.info.source and result.info.source.source:
            source_info = result.info.source
        else:
            try:
                obj, _, _ = resolve_dotted_path(result.target)
                source_info = extract_source(obj)
            except Exception as e:
                self.console.print(f"[red]Error getting source: {e}[/red]")
                return

        if source_info.is_builtin or not source_info.source:
            self.console.print("[yellow]Source code not available (built-in or C extension)[/yellow]")
            if source_info.file_path:
                self.console.print(f"[dim]File: {source_info.file_path}[/dim]")
            return

        syntax = Syntax(
            source_info.source,
            "python",
            theme="monokai",
            line_numbers=True,
            start_line=source_info.start_line or 1,
        )
        self.console.print(syntax)

        if source_info.file_path:
            self.console.print(f"\n[dim]File: {source_info.file_path}[/dim]")

    def print_docstring(self, result: InspectionResult) -> None:
        """Print docstring only."""
        if result.info.docstring:
            self.console.print(
                Panel(
                    Markdown(result.info.docstring),
                    title=f"Documentation: {result.target}",
                    border_style="blue",
                )
            )
        else:
            self.console.print("[dim]No docstring available[/dim]")

    def print_signature(self, result: InspectionResult) -> None:
        """Print signature only."""
        info = result.info
        if info.signature:
            text = self._format_signature(info.name, info.signature)
            self.console.print(text)
        elif isinstance(info, ClassInfo) and info.signature:
            text = self._format_signature(info.name, info.signature, is_class=True)
            self.console.print(text)
        else:
            self.console.print("[dim]No signature available[/dim]")

    def print_json(self, result: InspectionResult) -> None:
        """Print as JSON."""

        def encoder(obj: Any) -> Any:
            if hasattr(obj, "value"):  # Enum
                return obj.name
            raise TypeError(f"Cannot serialize {type(obj)}")

        data = asdict(result)
        self.console.print_json(json_module.dumps(data, default=encoder, indent=2))
