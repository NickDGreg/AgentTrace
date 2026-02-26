"""Repository-level structural checks for agent-friendly scaffolding."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

LAYERS = ("types", "config", "repo", "service", "runtime", "ui")
LAYER_ORDER = {layer: idx for idx, layer in enumerate(LAYERS)}
MODULE_LAYER = {
    "agenttrace.output": "types",
    "agenttrace.scoring": "types",
    "agenttrace.tasks": "types",
    "agenttrace.ground_truth": "repo",
    "agenttrace.run": "runtime",
    "agenttrace.run_isolated": "runtime",
}
PRINT_ALLOWED = {
    "agenttrace.run",
    "agenttrace.run_isolated",
    "agenttrace.scaffolding_checks",
}
MAX_LINES = {
    "agenttrace": 420,
    "tools": 320,
}
DATACLASS_SUFFIXES = (
    "Task",
    "Spec",
    "Result",
    "Config",
    "Event",
    "Record",
    "Violation",
)


@dataclass(slots=True)
class Violation:
    code: str
    message: str
    path: Path
    line: int

    def render(self) -> str:
        return f"{self.code}:{self.path}:{self.line}: {self.message}"


def run_all_checks(repo_root: Path) -> list[str]:
    violations: list[Violation] = []
    violations.extend(_check_layer_dependencies(repo_root))
    violations.extend(_check_print_calls(repo_root))
    violations.extend(_check_file_size_limits(repo_root))
    violations.extend(_check_dataclass_naming(repo_root))
    return sorted(v.render() for v in violations)


def _check_layer_dependencies(repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for path in _module_files(repo_root):
        module = _module_name_from_path(repo_root, path)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        src_layer = MODULE_LAYER.get(module)
        if src_layer is None:
            continue
        for imported_module, line in _iter_agenttrace_imports(module, tree):
            dst_layer = MODULE_LAYER.get(imported_module)
            if dst_layer is None:
                continue
            if LAYER_ORDER[dst_layer] > LAYER_ORDER[src_layer]:
                violations.append(
                    Violation(
                        code="LAYER001",
                        message=(
                            f"{module} ({src_layer}) cannot depend on "
                            f"{imported_module} ({dst_layer}); dependency direction is invalid."
                        ),
                        path=path,
                        line=line,
                    )
                )
    return violations


def _check_print_calls(repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for path in _module_files(repo_root):
        module = _module_name_from_path(repo_root, path)
        if not module.startswith("agenttrace."):
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "print":
                continue
            if module in PRINT_ALLOWED:
                continue
            violations.append(
                Violation(
                    code="LOG001",
                    message="print() is disallowed outside CLI runtime modules.",
                    path=path,
                    line=node.lineno,
                )
            )
    return violations


def _check_file_size_limits(repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for directory, max_lines in MAX_LINES.items():
        root = repo_root / directory
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            line_count = path.read_text(encoding="utf-8").count("\n") + 1
            if line_count > max_lines:
                violations.append(
                    Violation(
                        code="SIZE001",
                        message=(
                            f"file has {line_count} lines; limit for {directory}/ is {max_lines}."
                        ),
                        path=path,
                        line=1,
                    )
                )
    return violations


def _check_dataclass_naming(repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for path in _module_files(repo_root):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if not _is_dataclass(node):
                continue
            if node.name.endswith(DATACLASS_SUFFIXES):
                continue
            violations.append(
                Violation(
                    code="TYPE001",
                    message=(
                        "dataclass names must end with one of: "
                        + ", ".join(DATACLASS_SUFFIXES)
                    ),
                    path=path,
                    line=node.lineno,
                )
            )
    return violations


def _is_dataclass(node: ast.ClassDef) -> bool:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "dataclass":
            return True
        if isinstance(decorator, ast.Call):
            target = decorator.func
            if isinstance(target, ast.Name) and target.id == "dataclass":
                return True
            if isinstance(target, ast.Attribute) and target.attr == "dataclass":
                return True
    return False


def _module_files(repo_root: Path) -> Iterable[Path]:
    for package in ("agenttrace",):
        root = repo_root / package
        if not root.exists():
            continue
        yield from sorted(root.rglob("*.py"))


def _iter_agenttrace_imports(
    module_name: str, tree: ast.AST
) -> Iterable[tuple[str, int]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("agenttrace."):
                    yield alias.name, node.lineno
        if isinstance(node, ast.ImportFrom):
            resolved = _resolve_import_from(module_name, node)
            if resolved is None:
                continue
            if resolved == "agenttrace":
                continue
            if resolved.startswith("agenttrace."):
                yield resolved, node.lineno


def _resolve_import_from(module_name: str, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module

    base_parts = module_name.split(".")
    if module_name.endswith(".__init__"):
        package_parts = base_parts[:-1]
    else:
        package_parts = base_parts[:-1]

    trim = node.level - 1
    if trim > len(package_parts):
        return None

    parent = package_parts[: len(package_parts) - trim]
    if node.module:
        return ".".join([*parent, node.module])
    return ".".join(parent)


def _module_name_from_path(repo_root: Path, path: Path) -> str:
    rel = path.relative_to(repo_root).with_suffix("")
    return ".".join(rel.parts)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    violations = run_all_checks(repo_root)
    if not violations:
        print("scaffolding checks passed")
        return 0
    for line in violations:
        print(line)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
