import os
import sys

# Add src to path
sys.path.append(os.getcwd())

from src.core.services.compliance_docs.src.generators.base import BaseGenerator
from src.core.services.compliance_docs.src.generators.docx_generator import (
    DOCXGenerator,
)

print(f"BaseGenerator: {BaseGenerator}")
print(f"BaseGenerator bases: {BaseGenerator.__bases__}")
print(f"BaseGenerator dict: {BaseGenerator.__dict__.keys()}")
print(f"DOCXGenerator bases: {DOCXGenerator.__bases__}")

try:
    g = DOCXGenerator(output_dir="/tmp")
    print("DOCXGenerator instantiated successfully")
except Exception as e:
    import traceback

    traceback.print_exc()
    print(f"Error: {e}")
