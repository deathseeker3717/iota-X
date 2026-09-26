"""Symbol extraction and AST analysis for the AI Coding Harness.

Parses source code into structured symbol trees:
- Classes (methods, inheritance, docstrings)
- Functions & async functions (parameters, return types, decorators, calls)
- Imports & dependencies
- Global constants & variables
"""

from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class SymbolType(str, Enum):
    FUNCTION = "function"
    ASYNC_FUNCTION = "async_function"
    METHOD = "method"
    CLASS = "class"
    VARIABLE = "variable"
    IMPORT = "import"


@dataclass
class Symbol:
    """Represents a code symbol (class, function, method, variable)."""

    name: str
    symbol_type: SymbolType
    file_path: str
    start_line: int
    end_line: int
    signature: str = ""
    docstring: str = ""
    parent_symbol: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["symbol_type"] = self.symbol_type.value
        return d


@dataclass
class ImportItem:
    """Represents an imported module or symbol."""

    source_module: str
    imported_name: str
    alias: Optional[str] = None
    line_number: int = 1
    is_from_import: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FileSymbols:
    """All symbols and imports extracted from a single file."""

    file_path: str
    symbols: List[Symbol] = field(default_factory=list)
    imports: List[ImportItem] = field(default_factory=list)
    referenced_identifiers: Set[str] = field(default_factory=set)
    parse_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "symbols": [s.to_dict() for s in self.symbols],
            "imports": [i.to_dict() for i in self.imports],
            "referenced_identifiers": sorted(list(self.referenced_identifiers)),
            "parse_error": self.parse_error,
        }


class PythonSymbolVisitor(ast.NodeVisitor):
    """AST Visitor that extracts functions, classes, methods, imports, and calls."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.symbols: List[Symbol] = []
        self.imports: List[ImportItem] = []
        self.referenced_identifiers: Set[str] = field(default_factory=set)
        self._current_class: Optional[str] = None

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(
                ImportItem(
                    source_module=alias.name,
                    imported_name=alias.name,
                    alias=alias.asname,
                    line_number=node.lineno,
                    is_from_import=False,
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        for alias in node.names:
            self.imports.append(
                ImportItem(
                    source_module=mod,
                    imported_name=alias.name,
                    alias=alias.asname,
                    line_number=node.lineno,
                    is_from_import=True,
                )
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        decorators = [self._format_node(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node) or ""
        bases = [self._format_node(b) for b in node.bases]
        bases_str = f"({', '.join(bases)})" if bases else ""
        signature = f"class {node.name}{bases_str}"

        self.symbols.append(
            Symbol(
                name=node.name,
                symbol_type=SymbolType.CLASS,
                file_path=self.file_path,
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                signature=signature,
                docstring=docstring,
                decorators=decorators,
            )
        )

        prev_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_function(node, is_async=True)

    def _handle_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_async: bool,
    ) -> None:
        prefix = "async def " if is_async else "def "
        stype = (
            SymbolType.METHOD
            if self._current_class
            else (SymbolType.ASYNC_FUNCTION if is_async else SymbolType.FUNCTION)
        )
        full_name = (
            f"{self._current_class}.{node.name}" if self._current_class else node.name
        )

        params: List[str] = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self._format_node(arg.annotation)}"
            params.append(arg_str)

        ret_type = self._format_node(node.returns) if node.returns else None
        ret_str = f" -> {ret_type}" if ret_type else ""
        signature = f"{prefix}{node.name}({', '.join(params)}){ret_str}"

        decorators = [self._format_node(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node) or ""

        # Extract calls within this function
        calls: List[str] = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._format_node(child.func)
                if call_name:
                    calls.append(call_name)

        self.symbols.append(
            Symbol(
                name=full_name,
                symbol_type=stype,
                file_path=self.file_path,
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                signature=signature,
                docstring=docstring,
                parent_symbol=self._current_class,
                parameters=params,
                return_type=ret_type,
                decorators=decorators,
                calls=calls,
            )
        )

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        # Capture top-level constants / global variables
        if self._current_class is None:
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    val = self._format_node(node.value)
                    self.symbols.append(
                        Symbol(
                            name=target.id,
                            symbol_type=SymbolType.VARIABLE,
                            file_path=self.file_path,
                            start_line=node.lineno,
                            end_line=getattr(node, "end_lineno", node.lineno),
                            signature=f"{target.id} = {val}",
                        )
                    )
        self.generic_visit(node)

    def _format_node(self, node: Optional[ast.AST]) -> str:
        if node is None:
            return ""
        try:
            return ast.unparse(node)
        except Exception:
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Attribute):
                return f"{self._format_node(node.value)}.{node.attr}"
            return ""


class GenericRegexSymbolExtractor:
    """Regex-based symbol extractor for JS/TS/Go/Rust/C/etc."""

    # Matches JS/TS functions, classes, exports
    JS_TS_FUNCTION = re.compile(
        r"^(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\(([^)]*)\)",
        re.MULTILINE,
    )
    JS_TS_ARROW = re.compile(
        r"^(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>",
        re.MULTILINE,
    )
    JS_TS_CLASS = re.compile(
        r"^(?:export\s+)?class\s+([a-zA-Z0-9_$]+)(?:\s+extends\s+([a-zA-Z0-9_$]+))?",
        re.MULTILINE,
    )
    JS_TS_IMPORT = re.compile(
        r"^import\s+(?:\{([^}]+)\}|\*\s+as\s+([a-zA-Z0-9_$]+)|([a-zA-Z0-9_$]+))\s+from\s+['\"]([^'\"]+)['\"]",
        re.MULTILINE,
    )

    @classmethod
    def extract(cls, content: str, file_path: str) -> FileSymbols:
        symbols: List[Symbol] = []
        imports: List[ImportItem] = []
        lines = content.splitlines()

        # Find classes
        for m in cls.JS_TS_CLASS.finditer(content):
            name = m.group(1)
            line_no = content[: m.start()].count("\n") + 1
            extends_clause = f" extends {m.group(2)}" if m.group(2) else ""
            symbols.append(
                Symbol(
                    name=name,
                    symbol_type=SymbolType.CLASS,
                    file_path=file_path,
                    start_line=line_no,
                    end_line=line_no,
                    signature=f"class {name}{extends_clause}",
                )
            )

        # Find functions
        for m in cls.JS_TS_FUNCTION.finditer(content):
            name = m.group(1)
            params = [p.strip() for p in m.group(2).split(",") if p.strip()]
            line_no = content[: m.start()].count("\n") + 1
            symbols.append(
                Symbol(
                    name=name,
                    symbol_type=SymbolType.FUNCTION,
                    file_path=file_path,
                    start_line=line_no,
                    end_line=line_no,
                    signature=f"function {name}({', '.join(params)})",
                    parameters=params,
                )
            )

        # Find arrow functions
        for m in cls.JS_TS_ARROW.finditer(content):
            name = m.group(1)
            params = [p.strip() for p in m.group(2).split(",") if p.strip()]
            line_no = content[: m.start()].count("\n") + 1
            symbols.append(
                Symbol(
                    name=name,
                    symbol_type=SymbolType.FUNCTION,
                    file_path=file_path,
                    start_line=line_no,
                    end_line=line_no,
                    signature=f"const {name} = ({', '.join(params)}) =>",
                    parameters=params,
                )
            )

        # Find imports
        for m in cls.JS_TS_IMPORT.finditer(content):
            line_no = content[: m.start()].count("\n") + 1
            named, namespace, default_imp, module = m.group(1), m.group(2), m.group(3), m.group(4)
            imp_name = named or namespace or default_imp or module
            imports.append(
                ImportItem(
                    source_module=module,
                    imported_name=imp_name.strip(),
                    line_number=line_no,
                    is_from_import=True,
                )
            )

        return FileSymbols(file_path=file_path, symbols=symbols, imports=imports)


class SymbolExtractor:
    """Unified symbol extractor dispatching according to file type."""

    @classmethod
    def extract_from_code(cls, code: str, file_path: str = "<string>") -> FileSymbols:
        """Parse source code string into FileSymbols."""
        ext = Path(file_path).suffix.lower()

        if ext == ".py" or ext == "":
            try:
                tree = ast.parse(code, filename=file_path)
                visitor = PythonSymbolVisitor(file_path=file_path)
                visitor.visit(tree)

                # Extract identifier token names for reference search
                id_tokens = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", code))

                return FileSymbols(
                    file_path=file_path,
                    symbols=visitor.symbols,
                    imports=visitor.imports,
                    referenced_identifiers=id_tokens,
                )
            except SyntaxError as e:
                return FileSymbols(
                    file_path=file_path,
                    parse_error=f"SyntaxError on line {e.lineno}: {e.msg}",
                )
        elif ext in (".js", ".jsx", ".ts", ".tsx", ".mjs"):
            return GenericRegexSymbolExtractor.extract(code, file_path)
        else:
            # Generic token extraction
            id_tokens = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", code))
            return FileSymbols(file_path=file_path, referenced_identifiers=id_tokens)

    @classmethod
    def extract_from_file(cls, path: Path, rel_path: Optional[str] = None) -> FileSymbols:
        """Parse file from disk into FileSymbols."""
        relative = rel_path or str(path)
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = path.read_text(encoding="latin-1", errors="replace")
            except Exception as e:
                return FileSymbols(file_path=relative, parse_error=str(e))
        except Exception as e:
            return FileSymbols(file_path=relative, parse_error=str(e))

        return cls.extract_from_code(content, file_path=relative)
