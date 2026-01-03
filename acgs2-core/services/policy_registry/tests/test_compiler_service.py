"""
ACGS-2 Policy Registry - Compiler Service Tests
Constitutional Hash: cdd01ef066bc6cf2

Comprehensive test coverage for CompilerService including:
- OPA bundle compilation
- OPA test execution
- Mock compilation fallback
- Error handling
- Directory and file processing
"""

import os
import subprocess
import tarfile
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.services.compiler_service import CompilerService

# Constitutional hash constant
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def compiler_service():
    """Create a fresh CompilerService instance for testing."""
    return CompilerService()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_rego_file(temp_dir):
    """Create a sample Rego policy file."""
    file_path = os.path.join(temp_dir, "policy.rego")
    with open(file_path, "w") as f:
        f.write(
            """
package test.policy

default allow = false

allow {
    input.user == "admin"
}
"""
        )
    return file_path


@pytest.fixture
def sample_rego_directory(temp_dir):
    """Create a directory with multiple Rego files."""
    policy_dir = os.path.join(temp_dir, "policies")
    os.makedirs(policy_dir)

    # Create main policy
    with open(os.path.join(policy_dir, "main.rego"), "w") as f:
        f.write(
            """
package main

import data.auth

default allow = false

allow {
    auth.is_authenticated
}
"""
        )

    # Create auth policy
    with open(os.path.join(policy_dir, "auth.rego"), "w") as f:
        f.write(
            """
package auth

is_authenticated {
    input.token != ""
}
"""
        )

    # Create test file
    with open(os.path.join(policy_dir, "test_main.rego"), "w") as f:
        f.write(
            """
package main_test

import data.main

test_allow_authenticated {
    main.allow with input as {"token": "valid"}
}
"""
        )

    return policy_dir


@pytest.fixture
def nested_rego_directory(temp_dir):
    """Create a nested directory structure with Rego files."""
    base_dir = os.path.join(temp_dir, "nested_policies")
    os.makedirs(os.path.join(base_dir, "sub1"))
    os.makedirs(os.path.join(base_dir, "sub2", "deep"))

    # Root policy
    with open(os.path.join(base_dir, "root.rego"), "w") as f:
        f.write("package root\ndefault allow = true")

    # Sub1 policy
    with open(os.path.join(base_dir, "sub1", "sub1.rego"), "w") as f:
        f.write("package sub1\ndefault deny = false")

    # Deep nested policy
    with open(os.path.join(base_dir, "sub2", "deep", "deep.rego"), "w") as f:
        f.write("package deep\ndefault allow = false")

    # Non-rego file (should be ignored in mock mode)
    with open(os.path.join(base_dir, "readme.txt"), "w") as f:
        f.write("This is not a rego file")

    return base_dir


@pytest.fixture
def output_bundle_path(temp_dir):
    """Get path for output bundle."""
    return os.path.join(temp_dir, "bundle.tar.gz")


# =============================================================================
# OPA Available Tests
# =============================================================================


class TestOPACompilation:
    """Tests for compilation when OPA is available."""

    @pytest.mark.asyncio
    async def test_compile_bundle_with_opa_success(
        self, compiler_service, sample_rego_file, output_bundle_path
    ):
        """Test successful compilation with OPA."""
        mock_version = MagicMock()
        mock_version.returncode = 0

        mock_test = MagicMock()
        mock_test.returncode = 0
        mock_test.stdout = "PASS: 1/1"
        mock_test.stderr = ""

        mock_build = MagicMock()
        mock_build.returncode = 0
        mock_build.stderr = ""

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [mock_version, mock_test, mock_build]

            result = await compiler_service.compile_bundle(
                paths=[sample_rego_file], output_path=output_bundle_path
            )

            assert result is True
            assert mock_run.call_count == 3  # version, test, build

    @pytest.mark.asyncio
    async def test_compile_bundle_with_opa_skip_tests(
        self, compiler_service, sample_rego_file, output_bundle_path
    ):
        """Test compilation with OPA, skipping tests."""
        mock_version = MagicMock()
        mock_version.returncode = 0

        mock_build = MagicMock()
        mock_build.returncode = 0
        mock_build.stderr = ""

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [mock_version, mock_build]

            result = await compiler_service.compile_bundle(
                paths=[sample_rego_file], output_path=output_bundle_path, run_tests=False
            )

            assert result is True
            assert mock_run.call_count == 2  # version, build (no test)

    @pytest.mark.asyncio
    async def test_compile_bundle_with_entrypoints(
        self, compiler_service, sample_rego_file, output_bundle_path
    ):
        """Test compilation with entrypoints."""
        mock_version = MagicMock()
        mock_version.returncode = 0

        mock_build = MagicMock()
        mock_build.returncode = 0
        mock_build.stderr = ""

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [mock_version, mock_build]

            result = await compiler_service.compile_bundle(
                paths=[sample_rego_file],
                output_path=output_bundle_path,
                entrypoints=["test/policy/allow", "test/policy/deny"],
                run_tests=False,
            )

            assert result is True
            # Verify entrypoints were passed
            build_call = mock_run.call_args_list[1]
            cmd = build_call[0][0]
            assert "-e" in cmd
            assert "test/policy/allow" in cmd
            assert "test/policy/deny" in cmd

    @pytest.mark.asyncio
    async def test_compile_bundle_opa_test_failure(
        self, compiler_service, sample_rego_file, output_bundle_path
    ):
        """Test compilation fails when OPA tests fail."""
        mock_version = MagicMock()
        mock_version.returncode = 0

        mock_test = MagicMock()
        mock_test.returncode = 1
        mock_test.stdout = "FAIL: test_allow"
        mock_test.stderr = "Error in test"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [mock_version, mock_test]

            result = await compiler_service.compile_bundle(
                paths=[sample_rego_file], output_path=output_bundle_path
            )

            assert result is False
            # Build should not be called after test failure
            assert mock_run.call_count == 2

    @pytest.mark.asyncio
    async def test_compile_bundle_opa_build_failure(
        self, compiler_service, sample_rego_file, output_bundle_path
    ):
        """Test compilation fails when OPA build fails."""
        mock_version = MagicMock()
        mock_version.returncode = 0

        mock_test = MagicMock()
        mock_test.returncode = 0
        mock_test.stdout = "PASS"
        mock_test.stderr = ""

        mock_build = MagicMock()
        mock_build.returncode = 1
        mock_build.stderr = "Build error: invalid syntax"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [mock_version, mock_test, mock_build]

            result = await compiler_service.compile_bundle(
                paths=[sample_rego_file], output_path=output_bundle_path
            )

            assert result is False


# =============================================================================
# Mock Compilation Tests (OPA Not Available)
# =============================================================================


class TestMockCompilation:
    """Tests for mock compilation when OPA is not available."""

    @pytest.mark.asyncio
    async def test_mock_compile_single_file(
        self, compiler_service, sample_rego_file, output_bundle_path
    ):
        """Test mock compilation of single file."""
        with patch("subprocess.run", side_effect=FileNotFoundError("opa not found")):
            result = await compiler_service.compile_bundle(
                paths=[sample_rego_file], output_path=output_bundle_path
            )

            assert result is True
            assert os.path.exists(output_bundle_path)

            # Verify tarball contents
            with tarfile.open(output_bundle_path, "r:gz") as tar:
                names = tar.getnames()
                assert len(names) == 1
                assert names[0] == "policy.rego"

    @pytest.mark.asyncio
    async def test_mock_compile_directory(
        self, compiler_service, sample_rego_directory, output_bundle_path
    ):
        """Test mock compilation of directory."""
        with patch("subprocess.run", side_effect=FileNotFoundError("opa not found")):
            result = await compiler_service.compile_bundle(
                paths=[sample_rego_directory], output_path=output_bundle_path
            )

            assert result is True
            assert os.path.exists(output_bundle_path)

            # Verify tarball contains all .rego files
            with tarfile.open(output_bundle_path, "r:gz") as tar:
                names = tar.getnames()
                assert len(names) == 3  # main.rego, auth.rego, test_main.rego
                assert any("main.rego" in n for n in names)
                assert any("auth.rego" in n for n in names)
                assert any("test_main.rego" in n for n in names)

    @pytest.mark.asyncio
    async def test_mock_compile_nested_directory(
        self, compiler_service, nested_rego_directory, output_bundle_path
    ):
        """Test mock compilation of nested directory structure."""
        with patch("subprocess.run", side_effect=FileNotFoundError("opa not found")):
            result = await compiler_service.compile_bundle(
                paths=[nested_rego_directory], output_path=output_bundle_path
            )

            assert result is True

            # Verify tarball contains all nested .rego files
            with tarfile.open(output_bundle_path, "r:gz") as tar:
                names = tar.getnames()
                # Should have 3 .rego files, not the .txt
                rego_files = [n for n in names if n.endswith(".rego")]
                assert len(rego_files) == 3
                # Should not include readme.txt
                assert not any("readme.txt" in n for n in names)

    @pytest.mark.asyncio
    async def test_mock_compile_multiple_paths(
        self, compiler_service, sample_rego_file, sample_rego_directory, output_bundle_path
    ):
        """Test mock compilation with multiple paths."""
        with patch("subprocess.run", side_effect=FileNotFoundError("opa not found")):
            result = await compiler_service.compile_bundle(
                paths=[sample_rego_file, sample_rego_directory], output_path=output_bundle_path
            )

            assert result is True

            # Verify tarball contains files from both paths
            with tarfile.open(output_bundle_path, "r:gz") as tar:
                names = tar.getnames()
                # 1 file from sample_rego_file + 3 from sample_rego_directory
                assert len(names) == 4

    @pytest.mark.asyncio
    async def test_mock_compile_empty_directory(
        self, compiler_service, temp_dir, output_bundle_path
    ):
        """Test mock compilation of empty directory."""
        empty_dir = os.path.join(temp_dir, "empty")
        os.makedirs(empty_dir)

        with patch("subprocess.run", side_effect=FileNotFoundError("opa not found")):
            result = await compiler_service.compile_bundle(
                paths=[empty_dir], output_path=output_bundle_path
            )

            assert result is True
            assert os.path.exists(output_bundle_path)

            # Tarball should be empty (no .rego files)
            with tarfile.open(output_bundle_path, "r:gz") as tar:
                assert len(tar.getnames()) == 0


# =============================================================================
# OPA Version Check Tests
# =============================================================================


class TestOPAVersionCheck:
    """Tests for OPA availability detection."""

    @pytest.mark.asyncio
    async def test_opa_available_via_version_check(
        self, compiler_service, sample_rego_file, output_bundle_path
    ):
        """Test OPA is detected via version command."""
        mock_version = MagicMock()
        mock_version.returncode = 0

        mock_build = MagicMock()
        mock_build.returncode = 0

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [mock_version, mock_build]

            await compiler_service.compile_bundle(
                paths=[sample_rego_file], output_path=output_bundle_path, run_tests=False
            )

            # First call should be version check
            version_call = mock_run.call_args_list[0]
            assert version_call[0][0] == ["opa", "version"]

    @pytest.mark.asyncio
    async def test_opa_not_available_called_process_error(
        self, compiler_service, sample_rego_file, output_bundle_path
    ):
        """Test fallback when OPA version command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "opa")

            result = await compiler_service.compile_bundle(
                paths=[sample_rego_file], output_path=output_bundle_path
            )

            # Should fall back to mock compilation and succeed
            assert result is True
            assert os.path.exists(output_bundle_path)


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in compilation."""

    @pytest.mark.asyncio
    async def test_compile_with_nonexistent_path(self, compiler_service, output_bundle_path):
        """Test compilation with non-existent path."""
        with patch("subprocess.run", side_effect=FileNotFoundError("opa not found")):
            result = await compiler_service.compile_bundle(
                paths=["/nonexistent/path/policy.rego"], output_path=output_bundle_path
            )

            # Should succeed but bundle will be empty
            assert result is True

    @pytest.mark.asyncio
    async def test_compile_with_permission_error(
        self, compiler_service, sample_rego_file, temp_dir
    ):
        """Test compilation handles permission errors."""
        # Create read-only directory for output
        readonly_dir = os.path.join(temp_dir, "readonly")
        os.makedirs(readonly_dir)
        output_path = os.path.join(readonly_dir, "subdir", "bundle.tar.gz")

        with patch("subprocess.run", side_effect=FileNotFoundError("opa not found")):
            # This should fail because the parent directory doesn't exist
            result = await compiler_service.compile_bundle(
                paths=[sample_rego_file], output_path=output_path
            )

            # Should return False due to error
            assert result is False

    @pytest.mark.asyncio
    async def test_compile_handles_generic_exception(
        self, compiler_service, sample_rego_file, output_bundle_path
    ):
        """Test compilation handles generic exceptions."""
        with patch("subprocess.run", side_effect=RuntimeError("Unexpected error")):
            result = await compiler_service.compile_bundle(
                paths=[sample_rego_file], output_path=output_bundle_path
            )

            assert result is False


# =============================================================================
# Bundle Content Tests
# =============================================================================


class TestBundleContent:
    """Tests for bundle content verification."""

    @pytest.mark.asyncio
    async def test_bundle_preserves_directory_structure(
        self, compiler_service, nested_rego_directory, output_bundle_path
    ):
        """Test mock bundle preserves relative directory structure."""
        with patch("subprocess.run", side_effect=FileNotFoundError("opa not found")):
            result = await compiler_service.compile_bundle(
                paths=[nested_rego_directory], output_path=output_bundle_path
            )

            assert result is True

            with tarfile.open(output_bundle_path, "r:gz") as tar:
                names = tar.getnames()
                # Check relative paths are preserved
                deep_files = [n for n in names if "deep" in n]
                assert len(deep_files) > 0

    @pytest.mark.asyncio
    async def test_bundle_only_includes_rego_files(
        self, compiler_service, temp_dir, output_bundle_path
    ):
        """Test mock bundle only includes .rego files."""
        mixed_dir = os.path.join(temp_dir, "mixed")
        os.makedirs(mixed_dir)

        # Create various file types
        with open(os.path.join(mixed_dir, "policy.rego"), "w") as f:
            f.write("package test")
        with open(os.path.join(mixed_dir, "data.json"), "w") as f:
            f.write('{"key": "value"}')
        with open(os.path.join(mixed_dir, "readme.md"), "w") as f:
            f.write("# Readme")
        with open(os.path.join(mixed_dir, "script.sh"), "w") as f:
            f.write("#!/bin/bash")

        with patch("subprocess.run", side_effect=FileNotFoundError("opa not found")):
            result = await compiler_service.compile_bundle(
                paths=[mixed_dir], output_path=output_bundle_path
            )

            assert result is True

            with tarfile.open(output_bundle_path, "r:gz") as tar:
                names = tar.getnames()
                assert len(names) == 1
                assert names[0] == "policy.rego" or names[0].endswith("policy.rego")


# =============================================================================
# Command Construction Tests
# =============================================================================


class TestCommandConstruction:
    """Tests for OPA command construction."""

    @pytest.mark.asyncio
    async def test_build_command_includes_output_path(
        self, compiler_service, sample_rego_file, output_bundle_path
    ):
        """Test build command includes correct output path."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_build = MagicMock()
        mock_build.returncode = 0

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [mock_version, mock_build]

            await compiler_service.compile_bundle(
                paths=[sample_rego_file], output_path=output_bundle_path, run_tests=False
            )

            build_call = mock_run.call_args_list[1]
            cmd = build_call[0][0]
            assert "-o" in cmd
            assert output_bundle_path in cmd

    @pytest.mark.asyncio
    async def test_build_command_includes_paths(
        self, compiler_service, sample_rego_file, sample_rego_directory, output_bundle_path
    ):
        """Test build command includes all input paths."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_build = MagicMock()
        mock_build.returncode = 0

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [mock_version, mock_build]

            await compiler_service.compile_bundle(
                paths=[sample_rego_file, sample_rego_directory],
                output_path=output_bundle_path,
                run_tests=False,
            )

            build_call = mock_run.call_args_list[1]
            cmd = build_call[0][0]
            assert sample_rego_file in cmd
            assert sample_rego_directory in cmd

    @pytest.mark.asyncio
    async def test_test_command_includes_paths(
        self, compiler_service, sample_rego_file, output_bundle_path
    ):
        """Test test command includes all input paths."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_test = MagicMock()
        mock_test.returncode = 0
        mock_test.stdout = ""
        mock_test.stderr = ""
        mock_build = MagicMock()
        mock_build.returncode = 0

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [mock_version, mock_test, mock_build]

            await compiler_service.compile_bundle(
                paths=[sample_rego_file], output_path=output_bundle_path, run_tests=True
            )

            test_call = mock_run.call_args_list[1]
            cmd = test_call[0][0]
            assert cmd[0] == "opa"
            assert cmd[1] == "test"
            assert "-v" in cmd
            assert sample_rego_file in cmd


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_compile_empty_paths_list(self, compiler_service, output_bundle_path):
        """Test compilation with empty paths list."""
        with patch("subprocess.run", side_effect=FileNotFoundError("opa not found")):
            result = await compiler_service.compile_bundle(paths=[], output_path=output_bundle_path)

            assert result is True
            # Empty tarball should be created
            with tarfile.open(output_bundle_path, "r:gz") as tar:
                assert len(tar.getnames()) == 0

    @pytest.mark.asyncio
    async def test_compile_path_with_spaces(self, compiler_service, temp_dir, output_bundle_path):
        """Test compilation with paths containing spaces."""
        space_dir = os.path.join(temp_dir, "path with spaces")
        os.makedirs(space_dir)

        file_path = os.path.join(space_dir, "policy with spaces.rego")
        with open(file_path, "w") as f:
            f.write("package test")

        with patch("subprocess.run", side_effect=FileNotFoundError("opa not found")):
            result = await compiler_service.compile_bundle(
                paths=[space_dir], output_path=output_bundle_path
            )

            assert result is True

            with tarfile.open(output_bundle_path, "r:gz") as tar:
                names = tar.getnames()
                assert len(names) == 1

    @pytest.mark.asyncio
    async def test_compile_unicode_filenames(self, compiler_service, temp_dir, output_bundle_path):
        """Test compilation with unicode in filenames."""
        unicode_dir = os.path.join(temp_dir, "政策目录")
        os.makedirs(unicode_dir)

        file_path = os.path.join(unicode_dir, "政策.rego")
        with open(file_path, "w") as f:
            f.write("package test")

        with patch("subprocess.run", side_effect=FileNotFoundError("opa not found")):
            result = await compiler_service.compile_bundle(
                paths=[unicode_dir], output_path=output_bundle_path
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_compile_with_none_entrypoints(
        self, compiler_service, sample_rego_file, output_bundle_path
    ):
        """Test compilation with None entrypoints."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_build = MagicMock()
        mock_build.returncode = 0

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [mock_version, mock_build]

            result = await compiler_service.compile_bundle(
                paths=[sample_rego_file],
                output_path=output_bundle_path,
                entrypoints=None,
                run_tests=False,
            )

            assert result is True

            # Verify no -e flags in command
            build_call = mock_run.call_args_list[1]
            cmd = build_call[0][0]
            assert "-e" not in cmd

    @pytest.mark.asyncio
    async def test_compile_with_empty_entrypoints(
        self, compiler_service, sample_rego_file, output_bundle_path
    ):
        """Test compilation with empty entrypoints list."""
        mock_version = MagicMock()
        mock_version.returncode = 0
        mock_build = MagicMock()
        mock_build.returncode = 0

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [mock_version, mock_build]

            result = await compiler_service.compile_bundle(
                paths=[sample_rego_file],
                output_path=output_bundle_path,
                entrypoints=[],
                run_tests=False,
            )

            assert result is True


# =============================================================================
# Constitutional Compliance Tests
# =============================================================================


class TestConstitutionalCompliance:
    """Tests for constitutional compliance markers."""

    def test_module_has_constitutional_hash(self):
        """Test that the module has constitutional hash in docstring."""
        from app.services import compiler_service

        assert CONSTITUTIONAL_HASH in compiler_service.__doc__

    def test_constitutional_hash_constant(self):
        """Test constitutional hash constant is correct."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_compiler_service_class_exists(self):
        """Test CompilerService class exists and is properly defined."""
        from app.services.compiler_service import CompilerService

        assert hasattr(CompilerService, "compile_bundle")

    @pytest.mark.asyncio
    async def test_compiler_service_is_async(self, compiler_service):
        """Test compile_bundle is an async method."""
        import inspect

        assert inspect.iscoroutinefunction(compiler_service.compile_bundle)


# =============================================================================
# Integration-style Tests
# =============================================================================


class TestIntegration:
    """Integration-style tests for the compiler service."""

    @pytest.mark.asyncio
    async def test_full_mock_compilation_workflow(
        self, compiler_service, sample_rego_directory, temp_dir
    ):
        """Test complete mock compilation workflow."""
        output_path = os.path.join(temp_dir, "workflow_bundle.tar.gz")

        with patch("subprocess.run", side_effect=FileNotFoundError("opa not found")):
            # Compile
            result = await compiler_service.compile_bundle(
                paths=[sample_rego_directory], output_path=output_path
            )

            assert result is True
            assert os.path.exists(output_path)

            # Extract and verify contents
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir)

            with tarfile.open(output_path, "r:gz") as tar:
                tar.extractall(extract_dir)

            # Verify extracted files contain Rego content
            extracted_files = []
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith(".rego"):
                        extracted_files.append(os.path.join(root, f))

            assert len(extracted_files) == 3

            # Read one file to verify content
            for ef in extracted_files:
                with open(ef, "r") as f:
                    content = f.read()
                    assert "package" in content

    @pytest.mark.asyncio
    async def test_multiple_compilations_sequential(
        self, compiler_service, sample_rego_file, temp_dir
    ):
        """Test multiple sequential compilations."""
        with patch("subprocess.run", side_effect=FileNotFoundError("opa not found")):
            for i in range(3):
                output_path = os.path.join(temp_dir, f"bundle_{i}.tar.gz")
                result = await compiler_service.compile_bundle(
                    paths=[sample_rego_file], output_path=output_path
                )
                assert result is True
                assert os.path.exists(output_path)
