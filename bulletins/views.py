"""
bulletins/views.py — Workflow de publication des bulletins
==========================================================
YELEN SCHOOL v3.4

Vues :
  bulletins_index            — Sélecteur année / classe / trimestre
  bulletins_classe           — Tableau de bord bulletins d'une classe
  bulletin_saisir            — Saisie HTMX absences + appréciation conseil
  bulletin_publier           — Toggle publication (HTMX)
  bulletins_classe_publier   — Publier TOUS les bulletins d'une classe
"""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from inscriptions.models import Inscription
from parametres.models import AnneeScolaire, Classe
from pedagogie.models import MoyenneGenerale, Trimestre

from .models import Bulletin


def _get_etab(request):
    return getattr(request.user, 'etablissement', None)


# ─── INDEX ────────────────────────────────────────────────────────────

@login_required
def bulletins_index(request):
    """Sélecteur : choisir une classe et un trimestre pour accéder aux bulletins."""
    etab = _get_etab(request)
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut') if etab else AnneeScolaire.objects.none()
    annee_id = request.GET.get('annee')
    annee = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    classes = (
        Classe.objects.filter(etablissement=etab, actif=True).select_related('cycle').order_by('cycle__ordre', 'nom')
        if etab else Classe.objects.none()
    )
    trimestres = (
        Trimestre.objects.filter(annee_scolaire=annee).order_by('numero')
        if annee else Trimestre.objects.none()
    )

    # Statistiques rapides : nb bulletins publiés par trimestre (1 requête)
    stats_qs = (
        Bulletin.objects
        .filter(trimestre__in=trimestres, inscription__classe__etablissement=etab)
        .values('trimestre_id')
        .annotate(total=Count('id'), publies=Count('id', filter=Q(est_publie=True)))
    )
    stats_par_trimestre = {s['trimestre_id']: s for s in stats_qs}
    trimestres_avec_stats = [
        {
            'trimestre': t,
            'total': stats_par_trimestre.get(t.pk, {}).get('total', 0),
            'publies': stats_par_trimestre.get(t.pk, {}).get('publies', 0),
        }
        for t in trimestres
    ]

    return render(request, 'bulletins/index.html', {
        'annee': annee,
        'annees': annees,
        'classes': classes,
        'trimestres': trimestres,
        'trimestres_avec_stats': trimestres_avec_stats,
    })


# ─── BULLETINS D'UNE CLASSE ───────────────────────────────────────────

@login_required
def bulletins_classe(request, class_id, trimestre_id):
    """Liste les bulletins de tous les élèves d'une classe pour un trimestre."""
    etab = getattr(request.user, 'etablissement', None)
    if etab:
        classe = get_object_or_404(Classe, pk=class_id, etablissement=etab)
    else:
        classe = get_object_or_404(Classe, pk=class_id)
    trimestre = get_object_or_404(Trimestre, pk=trimestre_id)

    inscriptions = (
        Inscription.objects
        .filter(classe=classe, annee_scolaire=trimestre.annee_scolaire)
        .exclude(statut='ABANDON')
        .select_related('eleve')
        .order_by('eleve__nom', 'eleve__prenom')
    )

    # Charger (ou créer) les bulletins pour chaque inscription
    bulletins_par_ins = {
        b.inscription_id: b
        for b in Bulletin.objects.filter(trimestre=trimestre, inscription__in=inscriptions)
    }
    # Charger les moyennes générales calculées
    mg_par_ins = {
        mg.inscription_id: mg
        for mg in MoyenneGenerale.objects.filter(trimestre=trimestre, inscription__in=inscriptions)
    }

    lignes = []
    for ins in inscriptions:
        bulletin = bulletins_par_ins.get(ins.pk)
        mg = mg_par_ins.get(ins.pk)
        lignes.append({
            'inscription': ins,
            'bulletin': bulletin,
            'mg': mg,
            'moyenne_calculee': mg is not None,
        })

    nb_total = len(lignes)
    nb_publies = sum(1 for l in lignes if l['bulletin'] and l['bulletin'].est_publie)
    nb_moyennes = sum(1 for l in lignes if l['moyenne_calculee'])

    if request.headers.get('HX-Request') and request.GET.get('_partial') == 'stats':
        tpl = 'bulletins/partials/bulletins_stats.html'
    else:
        tpl = 'bulletins/partials/bulletins_classe_table.html' if request.headers.get('HX-Request') else 'bulletins/bulletins_classe.html'
    return render(request, tpl, {
        'classe': classe,
        'trimestre': trimestre,
        'lignes': lignes,
        'nb_total': nb_total,
        'nb_publies': nb_publies,
        'nb_moyennes': nb_moyennes,
    })


# ─── SAISIE BULLETIN (HTMX) ───────────────────────────────────────────

@login_required
def bulletin_saisir(request, inscription_id, trimestre_id):
    """
    Affiche ou traite le formulaire de saisie d'un bulletin.
    Crée le Bulletin s'il n'existe pas encore.
    Compatible HTMX : retourne uniquement le fragment de ligne.
    """
    etab = getattr(request.user, 'etablissement', None)
    inscription = get_object_or_404(
        Inscription.objects.select_related('eleve', 'classe'),
        pk=inscription_id,
    )
    
    if etab and inscription.classe.etablissement_id != etab.pk:
        from django.contrib import messages
        messages.error(request, "Accès refusé. Cette inscription n'appartient pas à votre établissement.")
        return redirect('bulletins:bulletin_list')
    
    trimestre = get_object_or_404(Trimestre, pk=trimestre_id)
    bulletin, _ = Bulletin.objects.get_or_create(
        inscription=inscription,
        trimestre=trimestre,
    )
    mg = MoyenneGenerale.objects.filter(inscription=inscription, trimestre=trimestre).first()

    if request.method == 'POST':
        d = request.POST
        try:
            bulletin.absences_justifiees = int(d.get('absences_justifiees', 0) or 0)
            bulletin.absences_non_justifiees = int(d.get('absences_non_justifiees', 0) or 0)
            bulletin.retards = int(d.get('retards', 0) or 0)
            bulletin.appreciation_conseil = d.get('appreciation_conseil', '').strip()
            bulletin.save()
            # Synchroniser l'observation dans MoyenneGenerale si elle existe
            if mg and bulletin.appreciation_conseil:
                mg.observation_generale = bulletin.appreciation_conseil
                mg.save(update_fields=['observation_generale', 'updated_at'])
        except (ValueError, TypeError) as e:
            return render(request, 'bulletins/partials/bulletin_form.html', {
                'inscription': inscription,
                'trimestre': trimestre,
                'bulletin': bulletin,
                'mg': mg,
                'error': str(e),
            })
        return HttpResponse(status=204, headers={'HX-Trigger': 'bulletinUpdated'})

    return render(request, 'bulletins/partials/bulletin_form.html', {
        'inscription': inscription,
        'trimestre': trimestre,
        'bulletin': bulletin,
        'mg': mg,
    })


# ─── PUBLICATION (HTMX) ───────────────────────────────────────────────

@login_required
@require_POST
def bulletin_publier(request, inscription_id, trimestre_id):
    """
    Toggle publication d'un bulletin individuel.
    Crée le Bulletin si nécessaire.
    """
    etab = getattr(request.user, 'etablissement', None)
    inscription = get_object_or_404(Inscription, pk=inscription_id)
    
    if etab and inscription.classe.etablissement_id != etab.pk:
        from django.contrib import messages
        messages.error(request, "Accès refusé.")
        return JsonResponse({'error': 'Accès refusé'}, status=403)
    
    trimestre = get_object_or_404(Trimestre, pk=trimestre_id)
    bulletin, _ = Bulletin.objects.get_or_create(
        inscription=inscription,
        trimestre=trimestre,
    )
    mg = MoyenneGenerale.objects.filter(inscription=inscription, trimestre=trimestre).first()

    if bulletin.est_publie:
        bulletin.depublier()
        toast = {'type': 'info', 'message': f"Bulletin de {inscription.eleve.get_nom_complet()} dépublié."}
    else:
        try:
            bulletin.publier(request.user)
        except ValueError:
            resp = HttpResponse(status=422)
            resp['HX-Trigger'] = json.dumps({'showToast': {'type': 'error', 'message': "Impossible de publier : la moyenne n'a pas encore été calculée."}})
            return resp
        toast = {'type': 'success', 'message': f"Bulletin de {inscription.eleve.get_nom_complet()} publié avec succès."}
        # SMS au parent après publication individuelle
        from django.conf import settings as _settings
        if getattr(_settings, 'SMS_ENABLED', False):
            eleve = inscription.eleve
            numero = (
                eleve.telephone_parent
                or eleve.tuteur_telephone
                or eleve.telephone_urgence
                or ''
            )
            if numero:
                from core.tasks import envoyer_sms_async
                nom = eleve.get_nom_complet()
                etab_nom = getattr(inscription.classe.etablissement, 'nom', 'YELEN SCHOOL')
                lien = request.build_absolute_uri(
                    f"/bulletins/parent/{bulletin.token_signature}/"
                ) if bulletin.token_signature else ''
                msg = (
                    f"Bonjour, le bulletin de {nom} ({trimestre.nom}) est disponible."
                    + (f" Consultez et signez : {lien}" if lien else "")
                    + f" — {etab_nom}"
                )
                envoyer_sms_async(numero, msg)

    response = render(request, 'bulletins/partials/bulletin_ligne.html', {
        'inscription': inscription,
        'bulletin': bulletin,
        'mg': mg,
        'trimestre': trimestre,
        'moyenne_calculee': mg is not None,
    })
    response['HX-Trigger'] = json.dumps({
        'showToast': toast,
        'bulletinUpdated': True,
    })
    return response


# ─── PUBLICATION EN MASSE ─────────────────────────────────────────────

@login_required
@require_POST
def bulletins_classe_publier(request, class_id, trimestre_id):
    """Publie tous les bulletins (avec moyenne calculée) d'une classe en une action."""
    etab = getattr(request.user, 'etablissement', None)
    classe = get_object_or_404(Classe, pk=class_id)
    
    if etab and classe.etablissement_id != etab.pk:
        from django.contrib import messages
        messages.error(request, "Accès refusé.")
        return JsonResponse({'error': 'Accès refusé'}, status=403)
    
    trimestre = get_object_or_404(Trimestre, pk=trimestre_id)

    inscriptions = (
        Inscription.objects
        .filter(classe=classe, annee_scolaire=trimestre.annee_scolaire)
        .exclude(statut='ABANDON')
    )
    # Seules les inscriptions avec une MoyenneGenerale calculée
    ins_avec_mg = set(
        MoyenneGenerale.objects
        .filter(trimestre=trimestre, inscription__in=inscriptions)
        .values_list('inscription_id', flat=True)
    )

    nb = 0
    numeros_sms = []  # (numero, nom_eleve) pour envoi SMS après commit

    for ins in inscriptions.select_related('eleve'):
        if ins.pk not in ins_avec_mg:
            continue
        bulletin, _ = Bulletin.objects.get_or_create(inscription=ins, trimestre=trimestre)
        if not bulletin.est_publie:
            bulletin.publier(request.user)
            nb += 1
            # Collecter le numéro du parent / tuteur
            eleve = ins.eleve
            numero = (
                eleve.telephone_parent
                or eleve.tuteur_telephone
                or eleve.telephone_urgence
                or ''
            )
            if numero:
                numeros_sms.append((numero.strip(), eleve.get_nom_complet()))

    # Envoi SMS asynchrone (ne bloque pas la réponse)
    if nb > 0 and numeros_sms:
        from django.conf import settings as _settings
        if getattr(_settings, 'SMS_ENABLED', False):
            from core.tasks import envoyer_sms_async
            for numero, nom_eleve in numeros_sms:
                msg = (
                    f"Bonjour, le bulletin de {nom_eleve} "
                    f"({trimestre.nom}) est disponible. "
                    f"Contactez l'etablissement pour le consulter. "
                    f"— {classe.etablissement.nom if hasattr(classe, 'etablissement') else 'YELEN SCHOOL'}"
                )
                envoyer_sms_async(numero, msg)

    messages.success(request, f"{nb} bulletin(s) publié(s) pour {classe.nom} — {trimestre.nom}.")
    return redirect('bulletins:bulletins_classe', class_id=class_id, trimestre_id=trimestre_id)


# ═══════════════════════════════════════════════════════════════════
# BULLETIN ANNUEL DE NOTES
# ═══════════════════════════════════════════════════════════════════

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.template.loader import render_to_string
try:
    from weasyprint import HTML
except Exception:  # ImportError ou OSError (libpango/cairo absents)
    HTML = None

from inscriptions.models import Inscription
from parametres.models import AnneeScolaire


class BulletinAnnuelIndexView(LoginRequiredMixin, View):
    """Index : sélecteur classe / année / élève pour le bulletin annuel."""
    
    template_name = "bulletins/bulletin_annuel_index.html"
    
    def get(self, request):
        etab = getattr(request.user, 'etablissement', None)
        
        # Classes de l'établissement
        from parametres.models import Classe
        classes = (
            Classe.objects.filter(etablissement=etab, actif=True)
            .select_related('cycle')
            .order_by('cycle__ordre', 'nom')
            if etab else Classe.objects.none()
        )
        
        # Années scolaires
        annees = (
            AnneeScolaire.objects.filter(etablissement=etab)
            .order_by('-date_debut')
            if etab else AnneeScolaire.objects.none()
        )
        
        classe_id = request.GET.get('classe')
        annee_id = request.GET.get('annee')
        eleve_id = request.GET.get('eleve')
        
        classe = None
        annee = None
        inscriptions = []
        eleve = None
        
        if classe_id:
            classe = get_object_or_404(Classe, pk=classe_id)
        if annee_id:
            annee = get_object_or_404(AnneeScolaire, pk=annee_id)
        
        if classe and annee:
            inscriptions = (
                Inscription.objects
                .filter(classe=classe, annee_scolaire=annee)
                .exclude(statut='ABANDON')
                .select_related('eleve')
                .order_by('eleve__nom', 'eleve__prenom')
            )
        
        if eleve_id:
            eleve = get_object_or_404(Inscription, pk=eleve_id)
        
        return render(request, self.template_name, {
            'classes': classes,
            'annees': annees,
            'classe': classe,
            'annee': annee,
            'inscriptions': inscriptions,
            'eleve': eleve,
        })


class BulletinAnnuelView(LoginRequiredMixin, View):
    """Affiche le bulletin annuel de notes d'un élève (vue navigateur avec base.html)."""

    template_name = "bulletins/bulletin_annuel_web.html"

    def get(self, request, inscription_id, annee_pk):
        inscription = get_object_or_404(
            Inscription.objects.select_related('eleve', 'classe', 'classe__etablissement'),
            pk=inscription_id,
        )
        annee = get_object_or_404(AnneeScolaire, pk=annee_pk)

        from pedagogie.views import _build_bulletin_annuel_context
        ctx = _build_bulletin_annuel_context(request, inscription, annee)
        return render(request, self.template_name, ctx)


class BulletinAnnuelPDFView(LoginRequiredMixin, View):
    """Génère le PDF du bulletin annuel de notes."""

    def get(self, request, inscription_id, annee_pk):
        if HTML is None:
            return HttpResponse(
                "La génération PDF n'est pas disponible sur ce serveur.",
                status=503,
            )
        inscription = get_object_or_404(
            Inscription.objects.select_related('eleve', 'classe', 'classe__etablissement'),
            pk=inscription_id,
        )
        annee = get_object_or_404(AnneeScolaire, pk=annee_pk)

        if HTML is None:
            messages.error(request, "La génération PDF n'est pas disponible sur ce serveur (WeasyPrint manquant).")
            return redirect('bulletins:bulletin_annuel')

        from pedagogie.views import _build_bulletin_annuel_context
        try:
            from licences.pdf_utils import get_licence_info_for_pdf as _get_lic_pdf
        except ImportError:
            _get_lic_pdf = None

        ctx = _build_bulletin_annuel_context(request, inscription, annee)
        if _get_lic_pdf:
            try:
                etab_lic = getattr(request.user, 'etablissement', None) or inscription.classe.etablissement
                ctx['licence_info'] = _get_lic_pdf(request.user, etab_lic)
            except Exception:
                pass

        html_string = render_to_string('pedagogie/pdf/bulletin_annuel.html', ctx,
                                       request=request)

        pdf_file = HTML(
            string=html_string,
            base_url=request.build_absolute_uri()
        ).write_pdf()

        filename = f"bulletin_annuel_{inscription.eleve.matricule}_{annee.libelle}.pdf"
        response = HttpResponse(pdf_file, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response


class BulletinAnnuelBatchPDFView(LoginRequiredMixin, View):
    """Génère un PDF groupé avec tous les bulletins annuels d'une classe."""

    def get(self, request, class_id, annee_pk):
        if HTML is None:
            return HttpResponse(
                "La génération PDF n'est pas disponible sur ce serveur.",
                status=503,
            )
        from django.template.loader import render_to_string
        from parametres.models import Classe
        from pedagogie.views import _build_bulletin_annuel_context
        from core.utils import get_etablissement_context

        if HTML is None:
            messages.error(request, "La génération PDF n'est pas disponible sur ce serveur (WeasyPrint manquant).")
            return redirect('bulletins:bulletin_annuel_index')

        classe = get_object_or_404(Classe, pk=class_id)
        annee = get_object_or_404(AnneeScolaire, pk=annee_pk)

        inscriptions = (
            Inscription.objects
            .select_related('eleve', 'classe__cycle')
            .filter(classe=classe, annee_scolaire=annee)
            .exclude(statut='ABANDON')
            .order_by('eleve__nom', 'eleve__prenom')
        )

        etab = classe.etablissement
        etab_context = get_etablissement_context(etab, request)
        try:
            from licences.pdf_utils import get_licence_info_for_pdf as _get_lic_pdf2
            lic_info = _get_lic_pdf2(request.user, etab)
        except Exception:
            lic_info = None

        students_data = [
            _build_bulletin_annuel_context(request, ins, annee)
            for ins in inscriptions
        ]

        html_string = render_to_string('pedagogie/pdf/bulletin_annuel_batch.html', {
            'classe': classe,
            'annee_scolaire': annee,
            'students_data': students_data,
            'identite': etab_context.get('identite'),
            'logo_url': etab_context.get('logo_url'),
            'etab_logo_url': etab_context.get('etab_logo_url'),
            'etablissement': etab,
            'licence_info': lic_info,
        })

        pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
        filename = f"Bulletins_Annuels_{classe.nom}_{annee.libelle.replace(' ', '_')}.pdf"
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


# ─────────────────────────────────────────────────────────────────────────────
# Signature électronique parentale (accès public par token)
# ─────────────────────────────────────────────────────────────────────────────

def bulletin_parent_consulter(request, token):
    """Page publique permettant au parent de consulter et signer le bulletin."""
    from django.utils import timezone as tz
    bulletin = get_object_or_404(Bulletin, token_signature=token)

    # S3 — expiration du lien public : token_valide vérifié AVANT toute divulgation
    if not bulletin.token_valide:
        return render(request, 'bulletins/bulletin_parent.html', {
            'erreur': "Ce lien de consultation n'est plus valide (expiré ou annulé).",
        })

    if not bulletin.est_publie:
        return render(request, 'bulletins/bulletin_parent.html', {
            'erreur': "Ce bulletin n'est pas encore disponible.",
        })

    mg = MoyenneGenerale.objects.filter(
        inscription=bulletin.inscription,
        trimestre=bulletin.trimestre,
    ).first()

    return render(request, 'bulletins/bulletin_parent.html', {
        'bulletin': bulletin,
        'mg': mg,
        'token': token,
        'token_valide': bulletin.token_valide,
        'eleve': bulletin.inscription.eleve,
        'classe': bulletin.inscription.classe,
        'trimestre': bulletin.trimestre,
    })


@require_POST
def bulletin_parent_signer(request, token):
    """Enregistre la signature parentale (accès public)."""
    from django.utils import timezone as tz
    bulletin = get_object_or_404(Bulletin, token_signature=token)

    if bulletin.est_publie and not bulletin.signe_le and bulletin.token_valide:
        nom = request.POST.get('nom_signataire', '').strip()[:100] or 'Parent'
        bulletin.signe_le = tz.now()
        bulletin.signe_par_nom = nom
        bulletin.save(update_fields=['signe_le', 'signe_par_nom', 'updated_at'])

    return redirect('bulletins:bulletin_parent_consulter', token=token)
