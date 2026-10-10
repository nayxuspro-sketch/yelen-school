"""
yelen_school/csp_middleware.py — Content Security Policy avec nonces
=====================================================================
Génère un nonce cryptographique par requête et l'injecte dans :
  - request.csp_nonce         → utilisable dans les templates Django
  - En-tête HTTP Content-Security-Policy de la réponse

La directive script-src remplace 'unsafe-inline' par 'nonce-{nonce}',
ce qui bloque tout script inline non noncé (protection XSS renforcée).

Styles : les éléments <style> exigent le nonce (style-src) ; les attributs
style="…" sont autorisés (style-src-attr 'unsafe-inline') — un attribut de
style ne peut pas exécuter de script, et les gabarits en comptent plus de
2 500 (largeurs, couleurs, mises en page) qui seraient sinon ignorés.

Usage dans les templates :
    <script nonce="{{ request.csp_nonce }}">...</script>
"""

import secrets


class CSPNonceMiddleware:
    """
    Middleware CSP : génère un nonce par requête et pose l'en-tête
    Content-Security-Policy sur chaque réponse HTML.
    """

    # Directives de base — communes à toutes les requêtes
    _CSP_BASE = (
        "default-src 'self'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        nonce = secrets.token_urlsafe(16)
        request.csp_nonce = nonce

        response = self.get_response(request)

        # Appliquer uniquement sur les réponses HTML (pas JSON, PDF, fichiers)
        content_type = response.get('Content-Type', '')
        if 'text/html' in content_type and 'Content-Security-Policy' not in response:
            csp_parts = list(self._CSP_BASE) + [
                f"script-src 'self' 'nonce-{nonce}'",
                f"style-src 'self' 'nonce-{nonce}'",
                "style-src-attr 'unsafe-inline'",
                "script-src-attr 'none'",
            ]
            response['Content-Security-Policy'] = '; '.join(csp_parts)

        return response
