"""
Utilitaire d'export Excel (openpyxl) — 100 % hors ligne, zéro CDN.

Usage :
    from core.excel import ExcelExport

    wb = ExcelExport("Élèves")
    wb.add_header(["Matricule", "Nom", "Prénom", "Classe"])
    for eleve in eleves:
        wb.add_row([eleve.matricule, eleve.nom, eleve.prenom, classe])
    return wb.response("eleves_2024.xlsx")
"""
import io
from django.http import HttpResponse

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    _HAS_OPENPYXL = True
except ImportError:
    _HAS_OPENPYXL = False

# Couleurs du design system YELEN
_COLOR_PRIMARY   = "2D5BE3"   # bleu principal
_COLOR_HEADER_BG = "2D5BE3"
_COLOR_HEADER_FG = "FFFFFF"
_COLOR_ROW_ALT   = "F0F4FF"   # bleu très clair pour lignes paires
_COLOR_BORDER    = "D1D5DB"


class ExcelExport:
    """Constructeur de fichier Excel avec mise en forme YELEN."""

    def __init__(self, titre: str = "Export"):
        if not _HAS_OPENPYXL:
            raise RuntimeError("openpyxl n'est pas installé (pip install openpyxl).")

        self.wb = openpyxl.Workbook()
        self.ws = self.wb.active
        self.ws.title = titre[:31]  # Limite Excel sur les noms d'onglets
        self._row = 1
        self._ncols = 0

        # Styles réutilisables
        self._header_font   = Font(bold=True, color=_COLOR_HEADER_FG, size=11)
        self._header_fill   = PatternFill("solid", fgColor=_COLOR_HEADER_BG)
        self._header_align  = Alignment(horizontal="center", vertical="center", wrap_text=True)
        self._data_align    = Alignment(vertical="center", wrap_text=False)
        self._alt_fill      = PatternFill("solid", fgColor=_COLOR_ROW_ALT)
        thin = Side(style="thin", color=_COLOR_BORDER)
        self._border        = Border(left=thin, right=thin, top=thin, bottom=thin)

    def add_title(self, text: str, subtitle: str = ""):
        """Ligne de titre en haut du fichier (optionnel)."""
        self.ws.merge_cells(start_row=self._row, start_column=1, end_row=self._row, end_column=max(self._ncols, 1))
        cell = self.ws.cell(row=self._row, column=1, value=text)
        cell.font = Font(bold=True, size=14, color=_COLOR_PRIMARY)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        self.ws.row_dimensions[self._row].height = 28
        self._row += 1

        if subtitle:
            self.ws.merge_cells(start_row=self._row, start_column=1, end_row=self._row, end_column=max(self._ncols, 1))
            c2 = self.ws.cell(row=self._row, column=1, value=subtitle)
            c2.font = Font(italic=True, size=10, color="6B7280")
            c2.alignment = Alignment(horizontal="center", vertical="center")
            self._row += 1

        self._row += 1  # Ligne vide

    def add_header(self, columns: list):
        """Ajoute une ligne d'en-tête formatée."""
        self._ncols = len(columns)
        self.ws.row_dimensions[self._row].height = 22
        for col_idx, label in enumerate(columns, 1):
            cell = self.ws.cell(row=self._row, column=col_idx, value=label)
            cell.font   = self._header_font
            cell.fill   = self._header_fill
            cell.alignment = self._header_align
            cell.border = self._border
        self._row += 1

    def add_row(self, values: list, highlight_color: str = None):
        """Ajoute une ligne de données."""
        alt = (self._row % 2 == 0)
        self.ws.row_dimensions[self._row].height = 18
        for col_idx, val in enumerate(values, 1):
            cell = self.ws.cell(row=self._row, column=col_idx, value=val)
            cell.alignment = self._data_align
            cell.border = self._border
            if highlight_color:
                cell.fill = PatternFill("solid", fgColor=highlight_color)
            elif alt:
                cell.fill = self._alt_fill
        self._row += 1

    def add_separator(self, label: str = ""):
        """Ajoute une ligne vide avec un label optionnel (séparateur de section)."""
        if label:
            cell = self.ws.cell(row=self._row, column=1, value=label)
            cell.font = Font(bold=True, size=10, color=_COLOR_PRIMARY)
        self._row += 1

    def auto_width(self, min_width: int = 10, max_width: int = 50):
        """Ajuste la largeur des colonnes automatiquement."""
        for col_idx in range(1, self._ncols + 1):
            col_letter = get_column_letter(col_idx)
            max_len = min_width
            for row in self.ws.iter_rows(min_col=col_idx, max_col=col_idx):
                for cell in row:
                    if cell.value:
                        max_len = min(max(max_len, len(str(cell.value)) + 2), max_width)
            self.ws.column_dimensions[col_letter].width = max_len

    def response(self, filename: str) -> HttpResponse:
        """Retourne un HttpResponse avec le fichier XLSX en pièce jointe."""
        self.auto_width()
        self.ws.freeze_panes = self.ws.cell(row=2, column=1)  # Fige la ligne d'en-tête

        buffer = io.BytesIO()
        self.wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
