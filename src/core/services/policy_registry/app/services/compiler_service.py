"""
Compiler Service for Policy Registry
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
import os
import subprocess
import tarfile
from typing import List, Optional

logger = logging.getLogger(__name__)


class CompilerService:
    """
    Service for compiling Rego policies into OPA bundles.
    """

    async def compile_bundle(
        self,
        paths: List[str],
        output_path: str,
        entrypoints: Optional[List[str]] = None,
        run_tests: bool = True,
    ) -> bool:
        """
        Compile specified policy files/directories into an OPA bundle (.tar.gz).
        """
        try:
            # Check if opa is available
            try:
                subprocess.run(["opa", "version"], check=True, capture_output=True)
                has_opa = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                has_opa = False
                logger.warning("OPA command not found, falling back to mock compilation")

            if has_opa:
                # Step 1: Run OPA tests if requested
                if run_tests:
                    test_cmd = ["opa", "test", "-v"] + paths
                    test_result = subprocess.run(test_cmd, capture_output=True, text=True)
                    if test_result.returncode != 0:
                        logger.error(
                            f"OPA tests failed:\n{test_result.stdout}\n{test_result.stderr}"
                        )
                        return False
                    logger.info("OPA tests passed successfully")

                # Step 2: Build bundle
                cmd = ["opa", "build", "-o", output_path]
                if entrypoints:
                    for ep in entrypoints:
                        cmd.extend(["-e", ep])
                cmd.extend(paths)

                logger.info(f"Running OPA build: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"OPA build failed: {result.stderr}")
                    return False
                logger.info(f"OPA bundle compiled successfully to {output_path}")
                return True
            else:
                # Mock compilation: Create a tarball with recursive directory scanning
                with tarfile.open(output_path, "w:gz") as tar:
                    for path in paths:
                        if os.path.isdir(path):
                            for root, _, files in os.walk(path):
                                for file in files:
                                    if file.endswith(".rego"):
                                        full_path = os.path.join(root, file)
                                        # Keep directory structure in tarball
                                        rel_path = os.path.relpath(full_path, os.path.dirname(path))
                                        tar.add(full_path, arcname=rel_path)
                        elif os.path.exists(path):
                            tar.add(path, arcname=os.path.basename(path))

                logger.info(f"Mock OPA bundle created at {output_path}")
                return True

        except Exception as e:
            logger.error(f"Compilation error: {e}")
            return False
