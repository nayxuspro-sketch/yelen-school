"""Archivage des PDF officiels et notification des comptes portail (parent et élève)."""
from django.core.files.base import ContentFile


def archiver_pdf_document(doc, prefixe: str, pdf_bytes: bytes) -> None:
    """Enregistre le fichier PDF sur ``doc`` puis notifie les comptes parent et élève liés."""
    from core.notifications import notifier_document_delivre

    nom = doc.inscription.eleve.nom.replace(' ', '_')
    doc.fichier.save(f"{prefixe}_{nom}_{doc.numero_document}.pdf", ContentFile(pdf_bytes), save=True)
    notifier_document_delivre(doc)
