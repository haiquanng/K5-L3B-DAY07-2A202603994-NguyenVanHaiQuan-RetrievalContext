"""Render source previews locally; requires PyMuPDF, no model/API calls."""
from pathlib import Path
import hashlib
import fitz

root = Path(__file__).resolve().parents[2]
pdf = root / 'pdf/BCTN_2025_ad403f779b.pdf'
expected = '9449a7251d126b635988974dbc72c2773c7fff39f4e5e858b5f7d3928b4e0e6c'
if hashlib.sha256(pdf.read_bytes()).hexdigest() != expected:
    raise ValueError('Source PDF differs from benchmark version; review previews before continuing.')
destination = root / 'web/public/documents'
destination.mkdir(parents=True, exist_ok=True)
with fitz.open(pdf) as document:
    for page in (1, 10, 31, 32, 33, 115):
        document[page - 1].get_pixmap(matrix=fitz.Matrix(1.2, 1.2)).save(destination / f'page-{page}.png')
print('Prepared 6 source page previews. The original PDF is unchanged.')
