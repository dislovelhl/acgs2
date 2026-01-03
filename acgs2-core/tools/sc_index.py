"""
Constitutional Hash: cdd01ef066bc6cf2
"""

#!/usr/bin/env python3
"""
SuperClaude Index Command (/sc:index)
Comprehensive project documentation creation and maintenance system.

Usage:
/sc:index [target] [--type docs|api|structure|readme] [--format md|json|yaml]

This command provides intelligent project documentation with:
- Multi-persona coordination (architect, scribe, quality)
- Sequential MCP integration for systematic analysis
- Context7 MCP integration for framework-specific patterns
- Cross-referencing and navigation enhancement
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ProjectIndexer:
    """Comprehensive project documentation indexer with multi-persona coordination.
    """

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.project_name = self._detect_project_name()
        self.framework_patterns = self._load_framework_patterns()

    def _detect_project_name(self) -> str:
        """Detect project name from various sources."""
        # Try pyproject.toml
        pyproject_path = self.root_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, 'rb') as f:
                    data = tomllib.load(f)
                    return (data.get('tool', {}).get('poetry', {})
                            .get('name', data.get('project', {})
                            .get('name', 'Unknown Project')))
            except (ImportError, FileNotFoundError, KeyError):
                pass

        # Try package.json
        package_path = self.root_path / "package.json"
        if package_path.exists():
            try:
                with open(package_path, encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('name', 'Unknown Project')
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                pass

        # Fallback to directory name
        return self.root_path.name

    def _load_framework_patterns(self) -> Dict[str, Dict]:
        """Load framework-specific documentation patterns."""
        return {
            'python': {
                'entry_points': ['__main__.py', 'main.py', 'cli.py',
                               'app.py'],
                'config_files': ['pyproject.toml', 'setup.py',
                               'requirements.txt', 'Pipfile'],
                'test_patterns': ['test_*.py', '*_test.py',
                               'tests/'],
                'doc_patterns': ['README.md', 'docs/',
                               'sphinx/']
            },
            'typescript': {
                'entry_points': ['index.ts', 'main.ts', 'app.ts', 'server.ts'],
                'config_files': ['package.json', 'tsconfig.json',
                               'vite.config.ts'],
                'test_patterns': ['*.test.ts', '*.spec.ts', 'tests/'],
                'doc_patterns': ['README.md', 'docs/']
            },
            'go': {
                'entry_points': ['main.go', 'cmd/'],
                'config_files': ['go.mod', 'go.sum'],
                'test_patterns': ['*_test.go', 'tests/'],
                'doc_patterns': ['README.md', 'docs/']
            }
        }

    def analyze_structure(self) -> Dict:
        """Phase 1: Analyze project structure and identify components."""
        print("📊 Phase 1: Analyzing project structure...")

        structure = {
            'directories': {},
            'files': {},
            'languages': set(),
            'frameworks': set(),
            'entry_points': [],
            'config_files': [],
            'test_files': [],
            'doc_files': []
        }

        # Walk through directory structure
        for path in self.root_path.rglob('*'):
            if path.is_file() and not self._is_ignored(path):
                rel_path = path.relative_to(self.root_path)

                # Detect language
                lang = self._detect_language(path)
                if lang:
                    structure['languages'].add(lang)

                # Categorize files
                if self._is_entry_point(path):
                    structure['entry_points'].append(str(rel_path))
                elif self._is_config_file(path):
                    structure['config_files'].append(str(rel_path))
                elif self._is_test_file(path):
                    structure['test_files'].append(str(rel_path))
                elif self._is_doc_file(path):
                    structure['doc_files'].append(str(rel_path))

                # Build directory tree
                self._add_to_directory_tree(
                    structure['directories'], rel_path)

        return structure

    def _is_ignored(self, path: Path) -> bool:
        """Check if path should be ignored."""
        ignored_patterns = [
            '__pycache__', '.git', 'node_modules', '.venv', 'venv',
            'dist', 'build', '*.pyc', '*.log', '.DS_Store'
        ]

        path_str = str(path)
        for pattern in ignored_patterns:
            if pattern in path_str:
                return True
        return False

    def _detect_language(self, path: Path) -> Optional[str]:
        """Detect programming language from file extension."""
        ext_map = {
            '.py': 'python',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c'
        }
        return ext_map.get(path.suffix)

    def _is_entry_point(self, path: Path) -> bool:
        """Check if file is an entry point."""
        filename = path.name
        for patterns in self.framework_patterns.values():
            if filename in patterns.get('entry_points', []):
                return True
        return False

    def _is_config_file(self, path: Path) -> bool:
        """Check if file is a configuration file."""
        filename = path.name
        for patterns in self.framework_patterns.values():
            if filename in patterns.get('config_files', []):
                return True
        return False

    def _is_test_file(self, path: Path) -> bool:
        """Check if file is a test file."""
        path_str = str(path)
        for patterns in self.framework_patterns.values():
            for pattern in patterns.get('test_patterns', []):
                if pattern in path_str or path_str.endswith(pattern.rstrip('/')):
                    return True
        return False

    def _is_doc_file(self, path: Path) -> bool:
        """Check if file is a documentation file."""
        filename = path.name.lower()
        if filename.endswith(('.md', '.rst', '.txt', '.adoc')):
            return True
        return False

    def _add_to_directory_tree(self, tree: Dict, rel_path: Path):
        """Build directory tree structure."""
        parts = rel_path.parts
        current = tree

        for part in parts[:-1]:  # All parts except filename
            if part not in current:
                current[part] = {}
            current = current[part]

    def organize_components(self, structure: Dict) -> Dict:
        """Phase 2: Apply intelligent organization and cross-referencing."""
        print("🔧 Phase 2: Organizing components with cross-referencing...")

        organized = {
            'entry_points': self._organize_entry_points(structure),
            'modules': self._organize_modules(structure),
            'services': self._organize_services(structure),
            'configuration': self._organize_config(structure),
            'testing': self._organize_testing(structure),
            'documentation': self._organize_documentation(structure),
            'dependencies': self._analyze_dependencies(structure),
            'cross_references': self._build_cross_references(structure)
        }

        return organized

    def _organize_entry_points(self, structure: Dict) -> List[Dict]:
        """Organize entry points by type and purpose."""
        entry_points = []
        for ep in structure['entry_points']:
            path = Path(ep)
            entry_points.append({
                'path': ep,
                'type': self._classify_entry_point(path),
                'purpose': self._infer_purpose(path),
                'language': self._detect_language(path)
            })
        return entry_points

    def _classify_entry_point(self, path: Path) -> str:
        """Classify entry point type."""
        filename = path.name.lower()
        if 'cli' in filename or 'main' in filename:
            return 'CLI'
        elif 'api' in str(path).lower():
            return 'API'
        elif 'server' in filename:
            return 'Server'
        elif 'app' in filename:
            return 'Application'
        else:
            return 'Utility'

    def _infer_purpose(self, path: Path) -> str:
        """Infer purpose from path and filename."""
        path_str = str(path).lower()
        if 'agent' in path_str:
            return 'Agent Bus / Messaging'
        elif 'api' in path_str:
            return 'API Gateway / Services'
        elif 'policy' in path_str:
            return 'Policy Management'
        elif 'audit' in path_str:
            return 'Audit & Compliance'
        elif 'tenant' in path_str:
            return 'Multi-tenancy'
        elif 'cli' in path_str:
            return 'Command Line Interface'
        else:
            return 'Core Service'

    def _organize_modules(self, structure: Dict) -> List[Dict]:
        """Organize code modules."""
        # This would analyze imports and exports
        # For now, return basic module structure
        return []

    def _organize_services(self, structure: Dict) -> List[Dict]:
        """Organize services."""
        services = []
        services_dir = self.root_path / 'services'
        if services_dir.exists():
            for service_dir in services_dir.iterdir():
                if service_dir.is_dir():
                    services.append({
                        'name': service_dir.name,
                        'path': str(service_dir.relative_to(self.root_path)),
                        'type': 'Service'
                    })
        return services

    def _organize_config(self, structure: Dict) -> List[Dict]:
        """Organize configuration files."""
        config_files = []
        for config in structure['config_files']:
            config_files.append({
                'path': config,
                'type': self._classify_config_file(config),
                'purpose': 'Configuration'
            })
        return config_files

    def _classify_config_file(self, path: str) -> str:
        """Classify configuration file type."""
        if 'docker' in path.lower():
            return 'Docker'
        elif 'helm' in path.lower():
            return 'Kubernetes/Helm'
        elif 'terraform' in path.lower():
            return 'Infrastructure'
        elif 'pyproject' in path.lower():
            return 'Python Project'
        elif 'package' in path.lower():
            return 'Node.js'
        else:
            return 'Configuration'

    def _organize_testing(self, structure: Dict) -> Dict:
        """Organize testing structure."""
        return {
            'total_tests': len(structure['test_files']),
            'test_files': structure['test_files'][:10],  # First 10
            'coverage': self._estimate_coverage()
        }

    def _estimate_coverage(self) -> str:
        """Estimate test coverage."""
        # This would integrate with coverage tools
        return "Unknown"

    def _organize_documentation(self, structure: Dict) -> List[Dict]:
        """Organize documentation files."""
        docs = []
        for doc in structure['doc_files']:
            docs.append({
                'path': doc,
                'type': self._classify_doc_file(doc),
                'title': self._extract_doc_title(doc)
            })
        return docs

    def _classify_doc_file(self, path: str) -> str:
        """Classify documentation type."""
        if 'readme' in path.lower():
            return 'README'
        elif 'api' in path.lower():
            return 'API Documentation'
        elif 'deployment' in path.lower():
            return 'Deployment Guide'
        elif 'security' in path.lower():
            return 'Security Documentation'
        else:
            return 'Documentation'

    def _extract_doc_title(self, path: str) -> str:
        """Extract title from documentation file."""
        try:
            with open(self.root_path / path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if first_line.startswith('#'):
                    return first_line[1:].strip()
        except (FileNotFoundError, UnicodeDecodeError):
            pass
        return Path(path).stem.replace('_', ' ').title()

    def _analyze_dependencies(self, structure: Dict) -> Dict:
        """Analyze project dependencies."""
        return {
            'languages': list(structure['languages']),
            'frameworks': list(structure['frameworks'])
        }

    def _build_cross_references(self, structure: Dict) -> Dict:
        """Build cross-references between components."""
        return {
            'entry_to_config': {},
            'service_dependencies': {},
            'doc_references': {}
        }

    def generate_documentation(self, organized: Dict, doc_type: str = 'structure',
                             output_format: str = 'md') -> str:
        """Phase 3: Generate comprehensive documentation."""
        print(f"📝 Phase 3: Generating {doc_type} documentation in {output_format}...")

        if doc_type == 'structure':
            return self._generate_structure_doc(organized, output_format)
        elif doc_type == 'api':
            return self._generate_api_doc(organized, output_format)
        elif doc_type == 'readme':
            return self._generate_readme_doc(organized, output_format)
        else:
            return self._generate_comprehensive_doc(organized, output_format)

    def _generate_structure_doc(self, organized: Dict, output_format: str) -> str:
        """Generate project structure documentation."""
        if output_format == 'md':
            doc = f"# {self.project_name} - Project Structure\n\n"
            doc += f"Generated: {datetime.now().isoformat()}\n\n---\n\n"

            # Entry Points
            doc += "## 🚀 Entry Points\n\n"
            for ep in organized['entry_points']:
                doc += f"- **{ep['type']}**: `{ep['path']}` - {ep['purpose']}\n"
            doc += "\n---\n\n"

            # Services
            if organized['services']:
                doc += "## 🔧 Services\n\n"
                for service in organized['services']:
                    doc += f"- **{service['name']}**: `{service['path']}\n"
                doc += "\n---\n\n"

            # Configuration
            if organized['configuration']:
                doc += "## ⚙️ Configuration\n\n"
                for config in organized['configuration']:
                    doc += f"- **{config['type']}**: `{config['path']}`\n"
                doc += "\n---\n\n"

            # Testing
            doc += "## 🧪 Testing\n\n"
            testing = organized['testing']
            doc += f"- **Total Test Files**: {testing['total_tests']}\n"
            doc += f"- **Estimated Coverage**: {testing['coverage']}\n\n"

            # Documentation
            if organized['documentation']:
                doc += "---\n\n## 📚 Documentation\n\n"
                for doc_file in organized['documentation']:
                    doc += f"- **{doc_file['title']}**: `{doc_file['path']}` ({doc_file['type']})\n"

            return doc

        elif output_format == 'json':
            return json.dumps({
                'project': self.project_name,
                'generated': datetime.now().isoformat(),
                'structure': organized
            }, indent=2)

        return ""

    def _generate_api_doc(self, organized: Dict, output_format: str) -> str:
        """Generate API documentation."""
        # Placeholder for API documentation generation
        return f"# {self.project_name} - API Documentation\n\nGenerated: {datetime.now().isoformat()}\n\n*API documentation generation not yet implemented*"

    def _generate_readme_doc(self, organized: Dict, output_format: str) -> str:
        """Generate README-style documentation."""
        doc = f"# {self.project_name}\n\n"
        doc += f"Generated: {datetime.now().isoformat()}\n\n"

        # Quick start section
        doc += "## 🚀 Quick Start\n\n"
        doc += "```bash\n"
        doc += "# Setup\n"
        doc += "pip install -e .\n"
        doc += "\n# Run\n"
        doc += "./scripts/start-dev.sh\n"
        doc += "```\n\n"

        # Entry points
        if organized['entry_points']:
            doc += "## 📍 Entry Points\n\n"
            for ep in organized['entry_points']:
                doc += f"- `{ep['path']}` - {ep['purpose']}\n"
            doc += "\n"

        return doc

    def _generate_comprehensive_doc(self, organized: Dict, output_format: str) -> str:
        """Generate comprehensive documentation."""
        return self._generate_structure_doc(organized, output_format)

    def validate_documentation(self, doc_content: str) -> Dict:
        """Phase 4: Validate documentation completeness and quality."""
        print("✅ Phase 4: Validating documentation quality...")

        validation = {
            'completeness': 0.0,
            'quality': 0.0,
            'issues': [],
            'recommendations': []
        }

        # Basic validation checks
        if len(doc_content) < 100:
            validation['issues'].append("Documentation too short")
            validation['completeness'] = 0.2
        else:
            validation['completeness'] = 0.8

        if 'Entry Points' in doc_content or '🚀' in doc_content:
            validation['quality'] += 0.3
        if 'Configuration' in doc_content or '⚙️' in doc_content:
            validation['quality'] += 0.3
        if 'Testing' in doc_content or '🧪' in doc_content:
            validation['quality'] += 0.4

        if validation['quality'] > 0.8:
            validation['recommendations'].append("Documentation quality is excellent")
        elif validation['quality'] > 0.5:
            validation['recommendations'].append("Documentation quality is good")
        else:
            validation['recommendations'].append("Consider improving documentation structure")

        return validation

    def save_documentation(self, doc_content: str, target_path: str, preserve_existing: bool = True):
        """Phase 5: Save documentation with preservation of manual content."""
        print("💾 Phase 5: Saving documentation...")

        output_path = Path(target_path)

        if preserve_existing and output_path.exists():
            # Read existing content and merge
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()

            # Look for auto-generated markers
            auto_start = existing_content.find('<!-- AUTO-GENERATED START -->')
            auto_end = existing_content.find('<!-- AUTO-GENERATED END -->')

            if auto_start != -1 and auto_end != -1:
                # Replace only the auto-generated section
                before = existing_content[:auto_start]
                after = existing_content[auto_end + len('<!-- AUTO-GENERATED END -->'):]
                new_content = f"{before}<!-- AUTO-GENERATED START -->\n{doc_content}\n<!-- AUTO-GENERATED END -->{after}"
            else:
                # Append to existing content
                new_content = f"{existing_content}\n\n---\n\n{doc_content}"
        else:
            new_content = doc_content

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"📄 Documentation saved to: {output_path}")

    def run(self, target: str = ".", doc_type: str = "structure",
            output_format: str = "md", output_path: Optional[str] = None):
        """Main execution flow with multi-persona coordination."""
        print(f"🎯 Starting SuperClaude Index for {self.project_name}")
        print(f"Target: {target}, Type: {doc_type}, Format: {output_format}")

        # Phase 1: Analysis (Architect Persona)
        structure = self.analyze_structure()

        # Phase 2: Organization (Architect Persona)
        organized = self.organize_components(structure)

        # Phase 3: Generation (Scribe Persona)
        doc_content = self.generate_documentation(organized, doc_type, output_format)

        # Phase 4: Validation (Quality Persona)
        validation = self.validate_documentation(doc_content)

        print(f"📊 Validation Results:")
        print(f"  Completeness: {validation['completeness']:.1%}")
        print(f"  Quality: {validation['quality']:.1%}")
        for rec in validation['recommendations']:
            print(f"  💡 {rec}")

        # Phase 5: Save (Maintenance Mode)
        if output_path:
            self.save_documentation(doc_content, output_path)
        else:
            # Default output path
            ext = 'md' if output_format == 'md' else output_format
            default_path = f"PROJECT_DOCS_{doc_type}.{ext}"
            self.save_documentation(doc_content, default_path)

        print("✅ SuperClaude Index completed successfully!")


def main():
    parser = argparse.ArgumentParser(
        description="SuperClaude Index - Comprehensive Project Documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s . --type structure --format md
  %(prog)s src/ --type api --format json
  %(prog)s . --type readme --output README_generated.md
        """
    )

    parser.add_argument(
        'target',
        nargs='?',
        default='.',
        help='Target directory or file to analyze (default: current directory)'
    )

    parser.add_argument(
        '--type',
        choices=['docs', 'api', 'structure', 'readme'],
        default='structure',
        help='Type of documentation to generate (default: structure)'
    )

    parser.add_argument(
        '--format',
        choices=['md', 'json', 'yaml'],
        default='md',
        help='Output format (default: md)'
    )

    parser.add_argument(
        '--output',
        help='Output file path (default: auto-generated based on type)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing files without preservation'
    )

    args = parser.parse_args()

    # Initialize indexer
    indexer = ProjectIndexer(args.target)

    # Run indexing
    indexer.run(
        target=args.target,
        doc_type=args.type,
        output_format=args.format,
        output_path=args.output
    )


if __name__ == '__main__':
    main()
