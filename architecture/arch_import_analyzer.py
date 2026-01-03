#!/usr/bin/env python3
"""
ARCH-001: Import Structure Analyzer
Constitutional Hash: cdd01ef066bc6cf2

Analyzes import relationships across ACGS-2 codebase to identify circular dependencies
and import optimization opportunities.
"""

import ast
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set

import matplotlib.pyplot as plt
import networkx as nx

# Constitutional hash for validation
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class ImportAnalyzer(ast.NodeVisitor):
    """Analyzes Python AST to extract import relationships."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.imports: Set[str] = set()  # Direct imports
        self.from_imports: Dict[str, Set[str]] = defaultdict(set)  # from X import Y
        self.relative_imports: Set[str] = set()  # relative imports
        self.aliases: Dict[str, str] = {}  # import aliases

    def visit_Import(self, node: ast.Import) -> None:
        """Handle regular imports: import module"""
        for alias in node.names:
            module_name = alias.name
            self.imports.add(module_name)
            if alias.asname:
                self.aliases[alias.asname] = module_name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle from imports: from module import name"""
        if node.module:
            module_name = node.module
            self.from_imports[module_name].update(alias.name for alias in node.names)
            # Also track the module itself
            self.imports.add(module_name)
        self.generic_visit(node)

    def get_module_name(self) -> str:
        """Convert file path to module name."""
        path = Path(self.file_path)
        if "acgs2-core" in str(path):
            # Convert to module path
            parts = path.relative_to(Path("acgs2-core")).parts
            if parts[-1].endswith(".py"):
                parts = parts[:-1] + (parts[-1][:-3],)
            return ".".join(parts)
        return str(path)


class CircularDependencyDetector:
    """Detects circular dependencies in import graph."""

    def __init__(self):
        self.graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)

    def add_dependency(self, importer: str, imported: str):
        """Add a dependency relationship."""
        self.graph[importer].add(imported)
        self.reverse_graph[imported].add(importer)

    def find_cycles(self) -> List[List[str]]:
        """Find all circular dependencies using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.graph.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor, path.copy()):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    return True

            rec_stack.remove(node)
            return False

        for node in self.graph:
            if node not in visited:
                dfs(node, [])

        return cycles

    def get_dependency_metrics(self) -> Dict[str, any]:
        """Calculate various dependency metrics."""
        # Most imported modules
        import_counts = defaultdict(int)
        for deps in self.graph.values():
            for dep in deps:
                import_counts[dep] += 1

        most_imported = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)

        # Most importing modules
        importing_counts = {module: len(deps) for module, deps in self.graph.items()}
        most_importing = sorted(importing_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_modules": len(self.graph),
            "total_dependencies": sum(len(deps) for deps in self.graph.values()),
            "most_imported": most_imported[:10],
            "most_importing": most_importing[:10],
            "cycles_found": len(self.find_cycles()),
        }


class ImportStructureAnalyzer:
    """Main analyzer for import structure across codebase."""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.analyzers: Dict[str, ImportAnalyzer] = {}
        self.detector = CircularDependencyDetector()

    def analyze_codebase(self) -> Dict[str, any]:
        """Analyze the entire codebase for import relationships."""
        print("🔍 Analyzing import structure...")

        # Find all Python files
        python_files = []
        for root, dirs, files in os.walk(self.root_path):
            # Skip virtual environment and other unwanted directories
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in ["__pycache__", ".venv", "node_modules"]
            ]

            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)

        print(f"📁 Found {len(python_files)} Python files")

        # Analyze each file
        for file_path in python_files:
            try:
                analyzer = self._analyze_file(file_path)
                if analyzer:
                    self.analyzers[str(file_path)] = analyzer
            except Exception as e:
                print(f"❌ Error analyzing {file_path}: {e}")

        # Build dependency graph
        self._build_dependency_graph()

        # Find cycles and metrics
        cycles = self.detector.find_cycles()
        metrics = self.detector.get_dependency_metrics()

        return {
            "files_analyzed": len(self.analyzers),
            "total_imports": sum(len(analyzer.imports) for analyzer in self.analyzers.values()),
            "circular_dependencies": cycles,
            "metrics": metrics,
            "analyzers": self.analyzers,
        }

    def _analyze_file(self, file_path: Path) -> Optional[ImportAnalyzer]:
        """Analyze a single Python file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            analyzer = ImportAnalyzer(str(file_path))
            tree = ast.parse(source, filename=str(file_path))
            analyzer.visit(tree)

            return analyzer
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
            return None

    def _build_dependency_graph(self):
        """Build the dependency graph from analyzed files."""
        for file_path, analyzer in self.analyzers.items():
            importer_module = analyzer.get_module_name()

            # Add all imports as dependencies
            for imported in analyzer.imports:
                # Resolve relative imports
                resolved_import = self._resolve_import(imported, file_path)
                if resolved_import:
                    self.detector.add_dependency(importer_module, resolved_import)

    def _resolve_import(self, import_name: str, from_file: str) -> Optional[str]:
        """Resolve an import name to a module path."""
        # This is a simplified resolver - in a real system you'd need
        # to handle sys.path, PYTHONPATH, etc.
        from_path = Path(from_file)

        # Handle relative imports
        if import_name.startswith("."):
            # Count dots to determine relative level
            dots = len(import_name) - len(import_name.lstrip("."))
            name_part = import_name[dots:]

            # Go up the directory tree
            current = from_path.parent
            for _ in range(dots - 1):  # -1 because we start from parent
                current = current.parent

            if name_part:
                target = current / name_part.replace(".", "/")
            else:
                target = current

            # Try to find the actual module
            if (target / "__init__.py").exists():
                return str(target.relative_to(self.root_path)).replace("/", ".")
            elif (target.parent / (target.name + ".py")).exists():
                return (
                    str((target.parent / target.name).relative_to(self.root_path))
                    .replace("/", ".")
                    .replace("\\", ".")
                )

        # For absolute imports within the project
        if "acgs2" in import_name:
            return import_name

        return None

    def generate_visualization(self, output_file: str = "import_graph.png"):
        """Generate a visualization of the import graph."""
        G = nx.DiGraph()

        # Add nodes and edges
        for importer, imports in self.detector.graph.items():
            for imported in imports:
                G.add_edge(importer, imported)

        # Draw the graph
        plt.figure(figsize=(20, 20))
        pos = nx.spring_layout(G, k=0.5, iterations=50)

        # Draw nodes
        nx.draw_networkx_nodes(G, pos, node_size=50, alpha=0.7)

        # Draw edges
        nx.draw_networkx_edges(G, pos, alpha=0.3, arrows=True, arrowsize=10)

        # Add labels for high-degree nodes only
        degrees = dict(G.degree())
        high_degree_nodes = {node: degrees[node] for node in degrees if degrees[node] > 5}
        nx.draw_networkx_labels(G, pos, labels=high_degree_nodes, font_size=8)

        plt.title("ACGS-2 Import Dependency Graph")
        plt.axis("off")
        plt.savefig(output_file, dpi=150, bbox_inches="tight")
        plt.close()

        print(f"📊 Import graph saved to {output_file}")


def main():
    """Main ARCH-001 analysis execution."""
    print("🏗️  ARCH-001: Import Structure Analysis")
    print("=" * 50)
    print("Constitutional Hash:", CONSTITUTIONAL_HASH)
    print()

    # Analyze the codebase
    analyzer = ImportStructureAnalyzer("acgs2-core")
    results = analyzer.analyze_codebase()

    print("📊 ANALYSIS RESULTS")
    print(f"Files analyzed: {results['files_analyzed']}")
    print(f"Total imports: {results['total_imports']}")
    print(f"Circular dependencies found: {len(results['circular_dependencies'])}")
    print()

    # Show metrics
    metrics = results["metrics"]
    print("📈 DEPENDENCY METRICS")
    print(f"Total modules: {metrics['total_modules']}")
    print(f"Total dependencies: {metrics['total_dependencies']}")
    print()

    print("🔝 MOST IMPORTED MODULES:")
    for module, count in metrics["most_imported"][:5]:
        print(f"  {module}: {count} imports")
    print()

    print("🔝 MOST IMPORTING MODULES:")
    for module, count in metrics["most_importing"][:5]:
        print(f"  {module}: {count} imports")
    print()

    # Show circular dependencies
    if results["circular_dependencies"]:
        print("🔄 CIRCULAR DEPENDENCIES FOUND:")
        for i, cycle in enumerate(results["circular_dependencies"][:5]):  # Show first 5
            print(f"  Cycle {i + 1}: {' -> '.join(cycle)}")
        if len(results["circular_dependencies"]) > 5:
            print(f"  ... and {len(results['circular_dependencies']) - 5} more")
    else:
        print("✅ NO CIRCULAR DEPENDENCIES FOUND")

    print()
    print("🎯 ARCH-001 ANALYSIS COMPLETE")
    print("✅ Import structure analyzed and circular dependencies identified")

    # Generate visualization if networkx is available
    try:
        analyzer.generate_visualization()
    except ImportError:
        print(
            "ℹ️  Install networkx and matplotlib for visualization: pip install networkx matplotlib"
        )


if __name__ == "__main__":
    main()
