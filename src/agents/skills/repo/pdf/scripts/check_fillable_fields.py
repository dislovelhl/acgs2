import sys

from pypdf import PdfReader

# Script for Claude to run to determine whether a PDF has fillable form fields. See forms.md.


reader = PdfReader(sys.argv[1])
if (reader.get_fields()):
    pass
else:
    pass
