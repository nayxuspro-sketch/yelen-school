// Analyse IA pour le bilan des périodes
function genererAnalyseIA() {
  var btn = document.getElementById('btn-ia');
  var label = document.getElementById('btn-ia-label');
  var errDiv = document.getElementById('ia-erreur');
  var sepIa = document.getElementById('sep-ia');
  var jsonEl = document.getElementById('stats-json');
  
  errDiv.style.display = 'none';
  errDiv.textContent = '';

  if (!jsonEl || !jsonEl.textContent.trim()) {
    errDiv.textContent = 'Aucune donnée disponible';
    errDiv.style.display = 'inline';
    return;
  }

  var stats = JSON.parse(jsonEl.textContent);

  btn.style.display = 'none';
  label.textContent = 'Génération...';

  // Get CSRF from hidden input
  var csrfToken = '';
  
  // First try the explicit csrf-token input we added
  var csrfInput = document.getElementById('csrf-token');
  if (csrfInput && csrfInput.value) {
    csrfToken = csrfInput.value;
  }
  
  // Fallback to any other csrf input
  if (!csrfToken) {
    var csrfInputs = document.querySelectorAll('[name=csrfmiddlewaretoken]');
    if (csrfInputs.length > 0) {
      csrfToken = csrfInputs[0].value;
      // Also update our hidden input
      if (csrfInput) csrfInput.value = csrfToken;
    }
  }
  
  console.log('CSRF Token:', csrfToken ? 'found' : 'not found');

  var url = '/pedagogie/resultats/bilan-periodes/analyse-ia/';
  console.log('URL:', url);
  
  // Send JSON as before
fetch(url, {
  method: 'POST',
  credentials: 'include',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrfToken,
    'Accept': 'application/json',
  },
  body: JSON.stringify({ stats: stats })
})
  .then(function(resp) { 
    console.log('Response status:', resp.status);
    console.log('Response headers:', resp.headers.get('content-type'));
    return resp.text();
  })
  .then(function(text) {
    console.log('Response text length:', text.length);
    if (text.indexOf('<!DOCTYPE') === 0) {
      console.log('Got HTML instead of JSON - probably CSRF error');
      throw new Error('CSRF error - got HTML response');
    }
    return JSON.parse(text);
  })
  .then(function(json) {
    if (json.commentaires) {
      for (var cle in json.commentaires) {
        var zone = document.getElementById('ia-' + cle);
        if (zone) {
          var analyse = json.commentaires[cle];
          var recosHtml = '';
          if (analyse.recommandations && analyse.recommandations.length > 0) {
            recosHtml = '<div style="margin-top:8px;"><strong>Recommandations:</strong><ul style="margin:4px 0 0 16px;">';
            analyse.recommandations.forEach(function(r) {
              recosHtml += '<li>' + r + '</li>';
            });
            recosHtml += '</ul></div>';
          }
          zone.innerHTML = '<div style="padding:12px; background:rgba(0,168,107,0.1); border-left:3px solid #00A86B; margin:8px 0;">' +
            '<div style="font-weight:bold; color:#00A86B; font-size:12px; text-transform:uppercase; margin-bottom:4px;">Analyse IA</div>' +
            '<div>' + analyse.commentaire + '</div>' + recosHtml +
            '</div>';
          zone.style.display = 'block';
        }
      }
      label.textContent = 'Analyse générée';
      sepIa.style.display = 'block';
      
      // Mettre à jour le champ caché pour le PDF
      var inputCommentaires = document.getElementById('input-commentaires');
      if (inputCommentaires) {
        inputCommentaires.value = JSON.stringify(json.commentaires);
      }
    } else if (json.erreur) {
      throw new Error(json.erreur);
    }
  })
  .catch(function(e) {
    errDiv.textContent = 'Erreur: ' + e.message;
    errDiv.style.display = 'inline';
    btn.style.display = 'inline-flex';
    label.textContent = 'Analyser avec l\'IA';
  });
}

// Détection offline (juste affichage)
function majEtatConnexion() {
  var badge = document.getElementById('badge-offline');
  if (badge) {
    badge.style.display = navigator.onLine ? 'none' : 'flex';
  }
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
  majEtatConnexion();
  window.addEventListener('online', majEtatConnexion);
  window.addEventListener('offline', majEtatConnexion);
  
  var btnIa = document.getElementById('btn-ia');
  if (btnIa && btnIa.onclick) {
    // already set
  } else if (btnIa) {
    btnIa.onclick = genererAnalyseIA;
  }
});