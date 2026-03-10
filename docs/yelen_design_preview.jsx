/**
 * YELEN SCHOOL — Design Preview v3.4
 * ─────────────────────────────────────────────────────────────────────────
 * Maquette interactive de référence visuelle.
 * Montre TOUS les composants tels qu'ils doivent être rendus dans l'app.
 * Sert de "traducteur" entre le design React et les templates Django/HTMX.
 *
 * Usage dans Antigravity :
 *   - Ouvrir ce fichier → clic droit → "Open in Browser View"
 *   - Naviguer entre les écrans via la barre en haut
 *   - Référencer un bloc JSX dans un prompt : "Convertis ce composant en template Django"
 *
 * Changelog :
 *   v1.0  — Dashboard, composants de base, sidebar
 *   v2.0  — Enregistrement élève (4 étapes), liste classes, carte ID
 *   v3.0  — ⭐ Signataires paramétrables (onglets cycle × type document)
 *           ⭐ Aperçu zone signature document PDF
 * ─────────────────────────────────────────────────────────────────────────
 */

import { useState } from "react";

// ─── DESIGN TOKENS ────────────────────────────────────────────────────────
const T = {
  bgApp:     "#0A1628",
  bgCard:    "#111E35",
  bgInput:   "#0D1B2E",
  bgHover:   "#162238",
  bgSelected:"#1A2A42",
  border:    "rgba(255,255,255,0.06)",
  borderFocus:"rgba(0,168,107,0.60)",
  primary:   "#00A86B",
  primaryDark:"#007A4D",
  primaryGlow:"rgba(0,168,107,0.35)",
  gold:      "#F5A623",
  danger:    "#DC3545",
  info:      "#17A2B8",
  textPrimary:  "#E8EDF5",
  textSecondary:"#9AAEC4",
  textMuted:    "#5A7A9A",
  fontInterface:"'Outfit', sans-serif",
  fontLogo:     "'Playfair Display', serif",
  fontMono:     "'DejaVu Sans Mono', monospace",
};

// ─── GLOBAL STYLES ────────────────────────────────────────────────────────
const G = `
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Playfair+Display:wght@700&display=swap');

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: ${T.fontInterface};
    background: ${T.bgApp};
    color: ${T.textPrimary};
    min-height: 100vh;
  }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes shimmer {
    0%   { background-position: -200% 0; }
    100% { background-position:  200% 0; }
  }
  @keyframes pulse {
    0%,100% { opacity: 1; }
    50%     { opacity: 0.45; }
  }

  .fade-up { animation: fadeUp 0.35s ease both; }
  .delay-1 { animation-delay: 0.06s; }
  .delay-2 { animation-delay: 0.12s; }
  .delay-3 { animation-delay: 0.18s; }
  .delay-4 { animation-delay: 0.24s; }

  ::-webkit-scrollbar { width: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 99px; }

  input, select, textarea {
    font-family: ${T.fontInterface};
    outline: none;
  }
  button { cursor: pointer; font-family: ${T.fontInterface}; }
`;

// ─── PRIMITIVES ───────────────────────────────────────────────────────────

const Card = ({ children, style = {}, className = "" }) => (
  <div className={`fade-up ${className}`} style={{
    background: T.bgCard,
    border: `1px solid ${T.border}`,
    borderRadius: 16,
    padding: 24,
    ...style,
  }}>{children}</div>
);

const Badge = ({ children, color = "primary" }) => {
  const colors = {
    primary:  { bg: "rgba(0,168,107,0.18)",  text: "#00C07A" },
    warning:  { bg: "rgba(245,166,35,0.18)", text: "#F5A623" },
    danger:   { bg: "rgba(220,53,69,0.18)",  text: "#FF6B7A" },
    info:     { bg: "rgba(23,162,184,0.18)", text: "#17A2B8" },
    neutral:  { bg: "rgba(154,174,196,0.12)",text: "#9AAEC4" },
  };
  const c = colors[color] || colors.neutral;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "2px 8px", borderRadius: 999,
      fontSize: 11, fontWeight: 700, letterSpacing: "0.05em",
      textTransform: "uppercase",
      background: c.bg, color: c.text,
    }}>{children}</span>
  );
};

const BtnPrimary = ({ children, onClick, style = {}, small = false }) => (
  <button onClick={onClick} style={{
    background: `linear-gradient(135deg, ${T.primary}, ${T.primaryDark})`,
    color: "#fff", border: "none",
    borderRadius: 10,
    padding: small ? "6px 14px" : "10px 22px",
    fontSize: small ? 12 : 14, fontWeight: 600,
    boxShadow: `0 4px 14px ${T.primaryGlow}`,
    transition: "all 0.2s ease",
    ...style,
  }}>{children}</button>
);

const BtnSecondary = ({ children, onClick, style = {}, small = false }) => (
  <button onClick={onClick} style={{
    background: "transparent",
    color: T.textPrimary,
    border: `1px solid ${T.border}`,
    borderRadius: 10,
    padding: small ? "6px 14px" : "10px 22px",
    fontSize: small ? 12 : 14, fontWeight: 500,
    transition: "all 0.2s ease",
    ...style,
  }}>{children}</button>
);

const Input = ({ label, placeholder, value, onChange, readonly = false, mono = false, style = {} }) => (
  <div style={{ marginBottom: 16 }}>
    {label && <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: T.textSecondary, marginBottom: 5 }}>{label}</label>}
    <input
      value={value || ""}
      onChange={onChange || (() => {})}
      placeholder={placeholder}
      readOnly={readonly}
      style={{
        width: "100%", background: readonly ? "#0D1525" : T.bgInput,
        border: `1px solid ${readonly ? T.border : T.border}`,
        borderStyle: readonly ? "dashed" : "solid",
        borderRadius: 10, padding: "10px 14px",
        color: readonly ? T.textMuted : T.textPrimary,
        fontSize: 14, fontFamily: mono ? T.fontMono : T.fontInterface,
        cursor: readonly ? "not-allowed" : "text",
        opacity: readonly ? 0.7 : 1,
        ...style,
      }}
    />
  </div>
);

const Select = ({ label, options, value, onChange }) => (
  <div style={{ marginBottom: 16 }}>
    {label && <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: T.textSecondary, marginBottom: 5 }}>{label}</label>}
    <select value={value} onChange={onChange} style={{
      width: "100%", background: T.bgInput,
      border: `1px solid ${T.border}`,
      borderRadius: 10, padding: "10px 14px",
      color: T.textPrimary, fontSize: 14,
      fontFamily: T.fontInterface,
      appearance: "none",
    }}>
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  </div>
);

const SectionTitle = ({ children }) => (
  <h3 style={{ fontSize: 16, fontWeight: 600, color: T.textSecondary, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 16, paddingBottom: 10, borderBottom: `1px solid ${T.border}` }}>
    {children}
  </h3>
);

const StatCard = ({ icon, value, label, color = T.primary, delay = "" }) => (
  <div className={`fade-up ${delay}`} style={{
    background: T.bgCard, border: `1px solid ${T.border}`,
    borderRadius: 16, padding: "20px 22px",
    display: "flex", alignItems: "center", gap: 16,
  }}>
    <div style={{
      width: 48, height: 48, borderRadius: 12,
      background: `${color}22`,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 22,
    }}>{icon}</div>
    <div>
      <div style={{ fontSize: 26, fontWeight: 700, color: T.textPrimary, lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 13, color: T.textSecondary, marginTop: 4 }}>{label}</div>
    </div>
  </div>
);

// ─── SIDEBAR ──────────────────────────────────────────────────────────────
const NAV = [
  { icon: "🏠", label: "Tableau de bord",   id: "dashboard" },
  { icon: "👥", label: "Élèves",             id: "eleves" },
  { icon: "📋", label: "Inscriptions",       id: "inscriptions" },
  { icon: "👨‍🏫", label: "Personnel",          id: "personnel" },
  { icon: "📄", label: "Documents",          id: "documents" },
  { icon: "💰", label: "Finances",           id: "finances" },
  { icon: "📊", label: "Présences",          id: "presences" },
  { icon: "⚙️", label: "Paramètres",         id: "parametres" },
];

const Sidebar = ({ active, onNav }) => (
  <aside style={{
    width: 240, minHeight: "100vh",
    background: T.bgCard, borderRight: `1px solid ${T.border}`,
    display: "flex", flexDirection: "column",
    position: "fixed", top: 0, left: 0, zIndex: 100,
  }}>
    {/* Logo */}
    <div style={{ padding: "28px 20px 20px", borderBottom: `1px solid ${T.border}` }}>
      <div style={{ fontFamily: T.fontLogo, fontSize: 20, color: T.primary, fontWeight: 700 }}>YELEN SCHOOL</div>
      <div style={{ fontSize: 11, color: T.textMuted, marginTop: 3 }}>Illuminer chaque parcours scolaire</div>
    </div>

    {/* Nav */}
    <nav style={{ flex: 1, padding: "12px 8px" }}>
      {NAV.map(item => (
        <div key={item.id} onClick={() => onNav(item.id)} style={{
          display: "flex", alignItems: "center", gap: 12,
          padding: "10px 14px", borderRadius: 10, margin: "2px 0",
          cursor: "pointer", fontSize: 14, fontWeight: 500,
          color: active === item.id ? T.primary : T.textSecondary,
          background: active === item.id ? "rgba(0,168,107,0.12)" : "transparent",
          borderLeft: active === item.id ? `3px solid ${T.primary}` : "3px solid transparent",
          transition: "all 0.15s ease",
        }}>
          <span style={{ fontSize: 16 }}>{item.icon}</span>
          {item.label}
        </div>
      ))}
    </nav>

    {/* User */}
    <div style={{ padding: "16px 20px", borderTop: `1px solid ${T.border}` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{
          width: 34, height: 34, borderRadius: "50%",
          background: `linear-gradient(135deg, ${T.primary}, ${T.primaryDark})`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 13, fontWeight: 700, color: "#fff",
        }}>DK</div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: T.textPrimary }}>KABORÉ Dramane</div>
          <div style={{ fontSize: 11, color: T.textMuted }}>Directeur</div>
        </div>
      </div>
    </div>
  </aside>
);

// ─── TOPBAR ───────────────────────────────────────────────────────────────
const Topbar = ({ title, subtitle }) => (
  <header style={{
    height: 64, background: T.bgCard,
    borderBottom: `1px solid ${T.border}`,
    display: "flex", alignItems: "center",
    justifyContent: "space-between",
    padding: "0 28px",
    position: "sticky", top: 0, zIndex: 50,
  }}>
    <div>
      <div style={{ fontSize: 16, fontWeight: 700, color: T.textPrimary }}>{title}</div>
      {subtitle && <div style={{ fontSize: 12, color: T.textMuted, marginTop: 1 }}>{subtitle}</div>}
    </div>
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <div style={{
        padding: "6px 14px", borderRadius: 8,
        background: "rgba(0,168,107,0.12)",
        fontSize: 12, fontWeight: 600, color: T.primary,
      }}>Année 2025-2026</div>
      <div style={{
        width: 36, height: 36, borderRadius: "50%",
        background: T.bgHover, display: "flex",
        alignItems: "center", justifyContent: "center",
        fontSize: 16, cursor: "pointer",
      }}>🔔</div>
    </div>
  </header>
);

// ═══════════════════════════════════════════════════════════════════════════
// ÉCRAN 1 — TABLEAU DE BORD
// ═══════════════════════════════════════════════════════════════════════════
const DashboardScreen = () => (
  <div>
    <Topbar title="Tableau de bord" subtitle="Lycée Municipal de Ouagadougou · Année 2025-2026" />
    <div style={{ padding: 28 }}>
      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 }}>
        <StatCard icon="👦" value="1 248" label="Élèves inscrits" color={T.primary} delay="delay-1" />
        <StatCard icon="👨‍🏫" value="87" label="Membres du personnel" color={T.info} delay="delay-2" />
        <StatCard icon="📄" value="34" label="Documents en attente" color={T.gold} delay="delay-3" />
        <StatCard icon="💰" value="2,4M" label="Paiements du mois (FCFA)" color="#A259FF" delay="delay-4" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20 }}>
        {/* Dernières inscriptions */}
        <Card className="delay-1">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div style={{ fontSize: 15, fontWeight: 600 }}>Dernières inscriptions</div>
            <BtnSecondary small>Voir tout</BtnSecondary>
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr>{["Matricule", "Nom & Prénom", "Classe", "Statut", "Date"].map(h => (
                <th key={h} style={{ textAlign: "left", padding: "8px 12px", fontSize: 11, fontWeight: 600, color: T.textSecondary, textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: `1px solid ${T.border}` }}>{h}</th>
              ))}</tr>
            </thead>
            <tbody>
              {[
                { mat: "BF-OUA-2026-0312", nom: "SAWADOGO Aminata", cls: "3ème B", statut: "Affectée", date: "08/03/2026", sc: "primary" },
                { mat: "BF-OUA-2026-0311", nom: "OUEDRAOGO Issouf", cls: "2nde A", statut: "Non affecté", date: "08/03/2026", sc: "warning" },
                { mat: "BF-OUA-2026-0310", nom: "KINDA Mariam", cls: "CM2", statut: "Boursière", date: "07/03/2026", sc: "info" },
                { mat: "BF-OUA-2026-0309", nom: "ZONGO Pascal", cls: "Tle C", statut: "Affecté", date: "07/03/2026", sc: "primary" },
              ].map((r, i) => (
                <tr key={i} style={{ borderBottom: `1px solid ${T.border}` }}>
                  <td style={{ padding: "11px 12px", fontFamily: T.fontMono, fontSize: 11, color: T.textSecondary }}>{r.mat}</td>
                  <td style={{ padding: "11px 12px", fontWeight: 500 }}>{r.nom}</td>
                  <td style={{ padding: "11px 12px", color: T.textSecondary }}>{r.cls}</td>
                  <td style={{ padding: "11px 12px" }}><Badge color={r.sc}>{r.statut}</Badge></td>
                  <td style={{ padding: "11px 12px", color: T.textMuted, fontSize: 12 }}>{r.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        {/* Activité récente */}
        <Card className="delay-2">
          <SectionTitle>Activité récente</SectionTitle>
          {[
            { icon: "📄", text: "CERT-LMO-2026-0089 émis", time: "il y a 8 min", color: T.primary },
            { icon: "👤", text: "Nouveau personnel enregistré", time: "il y a 23 min", color: T.info },
            { icon: "💳", text: "Paiement 45 000 FCFA reçu", time: "il y a 1h", color: T.gold },
            { icon: "📋", text: "34 réinscriptions validées", time: "il y a 2h", color: "#A259FF" },
            { icon: "⚠️", text: "3 élèves sans photo — carte ID", time: "il y a 3h", color: T.danger },
          ].map((a, i) => (
            <div key={i} style={{ display: "flex", gap: 12, padding: "10px 0", borderBottom: i < 4 ? `1px solid ${T.border}` : "none" }}>
              <div style={{ width: 34, height: 34, borderRadius: 10, background: `${a.color}18`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 15, flexShrink: 0 }}>{a.icon}</div>
              <div>
                <div style={{ fontSize: 13, color: T.textPrimary }}>{a.text}</div>
                <div style={{ fontSize: 11, color: T.textMuted, marginTop: 2 }}>{a.time}</div>
              </div>
            </div>
          ))}
        </Card>
      </div>
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════
// ÉCRAN 2 — ENREGISTREMENT ÉLÈVE (4 étapes)
// ═══════════════════════════════════════════════════════════════════════════
const EleveScreen = () => {
  const [step, setStep] = useState(0);
  const [age, setAge] = useState("");
  const [dob, setDob] = useState("");

  const steps = ["Identité civile", "Famille & contact", "Documents", "Statut & paramètres"];

  const calcAge = (val) => {
    setDob(val);
    if (!val) { setAge(""); return; }
    const d = new Date(val), today = new Date();
    let a = today.getFullYear() - d.getFullYear();
    if (today.getMonth() < d.getMonth() || (today.getMonth() === d.getMonth() && today.getDate() < d.getDate())) a--;
    setAge(`${a} an(s)`);
  };

  return (
    <div>
      <Topbar title="Enregistrement d'un élève" subtitle="Nouveau dossier" />
      <div style={{ padding: 28, maxWidth: 820 }}>

        {/* Indicateur d'étapes */}
        <div style={{ display: "flex", alignItems: "center", marginBottom: 32 }}>
          {steps.map((s, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", flex: i < steps.length - 1 ? 1 : "none" }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6, cursor: "pointer" }} onClick={() => setStep(i)}>
                <div style={{
                  width: 34, height: 34, borderRadius: "50%",
                  border: `2px solid ${i < step ? T.primary : i === step ? T.primary : T.border}`,
                  background: i < step ? T.primary : "transparent",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 13, fontWeight: 700,
                  color: i < step ? "#fff" : i === step ? T.primary : T.textMuted,
                }}>
                  {i < step ? "✓" : i + 1}
                </div>
                <span style={{ fontSize: 11, color: i === step ? T.primary : T.textMuted, whiteSpace: "nowrap" }}>{s}</span>
              </div>
              {i < steps.length - 1 && (
                <div style={{ flex: 1, height: 2, background: i < step ? T.primary : T.border, margin: "0 8px", marginBottom: 22 }} />
              )}
            </div>
          ))}
        </div>

        <Card>
          {step === 0 && (
            <div>
              <SectionTitle>Étape 1 — Identité civile</SectionTitle>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 20px" }}>
                <Input label="Nom de famille *" placeholder="Ex : SAWADOGO" />
                <Input label="Prénom(s) *" placeholder="Ex : Aminata" />
                <div>
                  <Input label="Date de naissance *" value={dob} onChange={e => calcAge(e.target.value)} />
                  {/* ⭐ Champ âge calculé automatiquement — lecture seule */}
                  <Input label="Âge (calculé automatiquement)" value={age} readonly placeholder="Âge calculé..." />
                </div>
                <Input label="Lieu de naissance *" placeholder="Ex : Ouagadougou" />
                <Select label="Sexe *" options={[{ value: "M", label: "Masculin" }, { value: "F", label: "Féminin" }]} value="F" onChange={() => {}} />
                <Input label="Nationalité" placeholder="Burkinabè" />
                <Input label="N° Extrait de naissance *" placeholder="Ex : 2013/B/0042" />
                <Input label="Langue maternelle" placeholder="Ex : Mooré (optionnel)" />
              </div>
            </div>
          )}
          {step === 1 && (
            <div>
              <SectionTitle>Étape 2 — Famille & contact</SectionTitle>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 20px" }}>
                <Input label="Nom du père" placeholder="NOM Prénom" />
                <Input label="Téléphone père" placeholder="Ex : +226 70 00 00 00" />
                <Input label="Nom de la mère" placeholder="NOM Prénom" />
                <Input label="Téléphone mère" placeholder="Ex : +226 75 00 00 00" />
                <Input label="Quartier de résidence" placeholder="Ex : Gounghin" />
                <Input label="Ville" placeholder="Ex : Ouagadougou" />
              </div>
            </div>
          )}
          {step === 2 && (
            <div>
              <SectionTitle>Étape 3 — Documents</SectionTitle>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                {["Photo d'identité *", "Acte de naissance *", "Carnet de vaccination", "Jugement supplétif"].map((doc, i) => (
                  <div key={i} style={{
                    border: `2px dashed ${T.border}`, borderRadius: 12,
                    padding: "24px 16px", textAlign: "center", cursor: "pointer",
                    transition: "border-color 0.2s",
                  }}>
                    <div style={{ fontSize: 28, marginBottom: 8 }}>📎</div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{doc}</div>
                    <div style={{ fontSize: 11, color: T.textMuted, marginTop: 4 }}>Cliquer pour uploader</div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {step === 3 && (
            <div>
              <SectionTitle>Étape 4 — Statut & paramètres</SectionTitle>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 20px" }}>
                <Select label="Statut élève" options={[
                  { value: "affecte", label: "Affecté par l'État" },
                  { value: "non_affecte", label: "Non affecté" },
                  { value: "boursier", label: "Boursier" },
                ]} value="affecte" onChange={() => {}} />
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: T.textSecondary, marginBottom: 10 }}>Options</label>
                  {[["Élève actif dans l'établissement", true], ["Exonéré des frais de scolarité", false]].map(([lbl, checked], i) => (
                    <label key={i} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10, cursor: "pointer" }}>
                      <div style={{
                        width: 20, height: 20, borderRadius: 5,
                        border: `2px solid ${checked ? T.primary : T.border}`,
                        background: checked ? T.primary : "transparent",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 12, color: "#fff", flexShrink: 0,
                      }}>{checked ? "✓" : ""}</div>
                      <span style={{ fontSize: 13, color: T.textPrimary }}>{lbl}</span>
                    </label>
                  ))}
                </div>
              </div>
              {/* Matricule auto-généré (lecture seule) */}
              <div style={{ background: "rgba(0,168,107,0.06)", border: `1px solid rgba(0,168,107,0.20)`, borderRadius: 12, padding: 16, marginTop: 8 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: T.primary, marginBottom: 6 }}>MATRICULE GÉNÉRÉ AUTOMATIQUEMENT</div>
                <div style={{ fontFamily: T.fontMono, fontSize: 16, fontWeight: 700, color: T.textPrimary, letterSpacing: "0.06em" }}>BF-OUA-2026-0313</div>
                <div style={{ fontSize: 11, color: T.textMuted, marginTop: 4 }}>Non modifiable après enregistrement</div>
              </div>
            </div>
          )}

          {/* Navigation */}
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 24, paddingTop: 20, borderTop: `1px solid ${T.border}` }}>
            <BtnSecondary onClick={() => setStep(Math.max(0, step - 1))}>← Précédent</BtnSecondary>
            {step < 3
              ? <BtnPrimary onClick={() => setStep(step + 1)}>Suivant →</BtnPrimary>
              : <BtnPrimary>✓ Enregistrer l'élève</BtnPrimary>
            }
          </div>
        </Card>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// ÉCRAN 3 — INSCRIPTION PAR MATRICULE (auto-remplissage)
// ═══════════════════════════════════════════════════════════════════════════
const InscriptionScreen = () => {
  const [recherche, setRecherche] = useState("");
  const [eleve, setEleve] = useState(null);

  const eleveDemo = {
    matricule: "BF-OUA-2025-0187",
    nom: "KABORE", prenom: "Oumarou",
    dob: "12/04/2012", age: "13 ans",
    statut: "Affecté", sexe: "M",
  };

  const handleSearch = (v) => {
    setRecherche(v);
    setEleve(v.length > 3 ? eleveDemo : null);
  };

  return (
    <div>
      <Topbar title="Inscription / Réinscription" subtitle="Année scolaire 2025-2026" />
      <div style={{ padding: 28, maxWidth: 820 }}>
        <Card>
          <SectionTitle>Sélection de l'élève par matricule</SectionTitle>

          {/* ⭐ Champ de recherche matricule + auto-remplissage */}
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: T.textSecondary, marginBottom: 6 }}>
              Matricule ou Nom / Prénom *
            </label>
            <input
              value={recherche}
              onChange={e => handleSearch(e.target.value)}
              placeholder="Saisir un matricule (BF-OUA-...) ou le nom de l'élève..."
              style={{
                width: "100%", background: T.bgInput, border: `1px solid ${T.borderFocus}`,
                borderRadius: 10, padding: "11px 14px",
                color: T.textPrimary, fontSize: 14,
                fontFamily: T.fontMono,
              }}
            />
            {recherche.length > 0 && recherche.length <= 3 && (
              <div style={{ fontSize: 12, color: T.textMuted, marginTop: 5 }}>Saisissez au moins 4 caractères...</div>
            )}
          </div>

          {/* Champs auto-remplis (lecture seule) */}
          {eleve && (
            <div style={{ animation: "fadeUp 0.3s ease both" }}>
              <div style={{ background: "rgba(0,168,107,0.06)", border: `1px solid rgba(0,168,107,0.20)`, borderRadius: 12, padding: "14px 16px", marginBottom: 20 }}>
                <div style={{ fontSize: 12, color: T.primary, fontWeight: 600, marginBottom: 8 }}>✓ Élève trouvé — champs remplis automatiquement (non modifiables)</div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0 20px" }}>
                  <Input label="Matricule" value={eleve.matricule} readonly mono />
                  <Input label="Nom" value={eleve.nom} readonly />
                  <Input label="Prénom" value={eleve.prenom} readonly />
                  <Input label="Date de naissance" value={eleve.dob} readonly />
                  <Input label="Âge" value={eleve.age} readonly />
                  <Input label="Statut" value={eleve.statut} readonly />
                </div>
              </div>

              <SectionTitle>Paramètres d'inscription</SectionTitle>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 20px" }}>
                <Select label="Classe *" options={[
                  { value: "", label: "— Sélectionner —" },
                  { value: "5b", label: "5ème B" },
                  { value: "5c", label: "5ème C" },
                ]} value="" onChange={() => {}} />
                <Select label="Année scolaire *" options={[{ value: "2025-2026", label: "2025-2026" }]} value="2025-2026" onChange={() => {}} />
              </div>
              <div style={{ marginTop: 16 }}>
                <BtnPrimary>✓ Valider l'inscription</BtnPrimary>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// ÉCRAN 4 — LISTE DOCUMENTS + FILE D'ATTENTE
// ═══════════════════════════════════════════════════════════════════════════
const DocumentsScreen = () => (
  <div>
    <Topbar title="Documents administratifs" subtitle="Gestion des demandes et émissions" />
    <div style={{ padding: 28 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 28 }}>
        <StatCard icon="⏳" value="12" label="En attente" color={T.gold} delay="delay-1" />
        <StatCard icon="✅" value="8" label="Émis aujourd'hui" color={T.primary} delay="delay-2" />
        <StatCard icon="📅" value="47" label="Émis ce mois" color={T.info} delay="delay-3" />
        <StatCard icon="🔄" value="3" label="En traitement" color="#A259FF" delay="delay-4" />
      </div>

      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div style={{ fontSize: 15, fontWeight: 600 }}>File d'attente des demandes</div>
          <BtnPrimary small>+ Nouvelle demande</BtnPrimary>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr>{["N°", "Type", "Élève", "Classe", "Demandé le", "Statut", "Actions"].map(h => (
              <th key={h} style={{ textAlign: "left", padding: "8px 12px", fontSize: 11, fontWeight: 600, color: T.textSecondary, textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: `1px solid ${T.border}` }}>{h}</th>
            ))}</tr>
          </thead>
          <tbody>
            {[
              { num: "CERT-LMO-2026-0090", type: "Certificat scolarité", nom: "SAWADOGO A.", cls: "3ème B", date: "09/03/2026", statut: "En attente", sc: "warning" },
              { num: "ATTEST-LMO-2026-0031", type: "Attestation", nom: "OUEDRAOGO I.", cls: "2nde A", date: "09/03/2026", statut: "En traitement", sc: "info" },
              { num: "AUTOR-LMO-2026-0018", type: "Autorisation absence", nom: "KINDA M.", cls: "CM2", date: "08/03/2026", statut: "Émis", sc: "primary" },
              { num: "CURSUS-LMO-2026-0007", type: "Cursus scolaire", nom: "ZONGO P.", cls: "Tle C", date: "08/03/2026", statut: "En attente", sc: "warning" },
            ].map((r, i) => (
              <tr key={i} style={{ borderBottom: `1px solid ${T.border}` }}>
                <td style={{ padding: "11px 12px", fontFamily: T.fontMono, fontSize: 11, color: T.textSecondary }}>{r.num}</td>
                <td style={{ padding: "11px 12px", fontWeight: 500 }}>{r.type}</td>
                <td style={{ padding: "11px 12px" }}>{r.nom}</td>
                <td style={{ padding: "11px 12px", color: T.textSecondary }}>{r.cls}</td>
                <td style={{ padding: "11px 12px", color: T.textMuted, fontSize: 12 }}>{r.date}</td>
                <td style={{ padding: "11px 12px" }}><Badge color={r.sc}>{r.statut}</Badge></td>
                <td style={{ padding: "11px 12px" }}>
                  <div style={{ display: "flex", gap: 6 }}>
                    <BtnPrimary small>Émettre</BtnPrimary>
                    <BtnSecondary small>Aperçu</BtnSecondary>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════
// ÉCRAN 5 — PARAMÈTRES → SIGNATAIRES ⭐ NOUVEAU v3.4
// ═══════════════════════════════════════════════════════════════════════════
const TYPE_DOCS = [
  { code: "CERT_SCOL",        label: "Certificat de Scolarité" },
  { code: "BULLETIN",         label: "Bulletin scolaire" },
  { code: "RECU_PAIEMENT",    label: "Reçu de paiement" },
  { code: "AUTORISATION",     label: "Autorisation d'absence" },
  { code: "ATTESTATION",      label: "Attestation de fréquentation" },
  { code: "CURSUS",           label: "Cursus scolaire" },
  { code: "CARTE_ID",         label: "Carte d'identité scolaire" },
  { code: "LISTE_CLASSE",     label: "Liste de classe" },
  { code: "LISTE_PERSONNEL",  label: "Liste du personnel" },
];

const CYCLES = [
  { id: 1, nom: "Préscolaire",    personnel: [] },
  { id: 2, nom: "Primaire",       personnel: [
    { id: 10, display: "KABORÉ Ousmane (Directeur de cycle)" },
    { id: 11, display: "SAWADOGO Aïcha (Directrice adjointe)" },
    { id: 12, display: "OUEDRAOGO Paul (Secrétaire)" },
  ]},
  { id: 3, nom: "Post-primaire",  personnel: [
    { id: 20, display: "TRAORÉ Mamadou (Proviseur)" },
    { id: 21, display: "ZONGO Fatimata (Censeure)" },
  ]},
  { id: 4, nom: "Secondaire",     personnel: [
    { id: 30, display: "DIALLO Ibrahim (Proviseur)" },
    { id: 31, display: "KINDA Aminata (Censeure)" },
    { id: 32, display: "BARRY Oumar (Directeur des études)" },
  ]},
];

const SignatairesScreen = () => {
  const [activeCycle, setActiveCycle] = useState(2);
  const [config, setConfig] = useState({});   // { "cycleId_CODE": { membreId, titre } }
  const [saved, setSaved] = useState(null);

  const key = (cId, code) => `${cId}_${code}`;

  const handleChange = (cId, code, field, value) => {
    setConfig(prev => ({
      ...prev,
      [key(cId, code)]: { ...(prev[key(cId, code)] || {}), [field]: value },
    }));
  };

  const save = (cId, code) => {
    setSaved(key(cId, code));
    setTimeout(() => setSaved(null), 2000);
  };

  const cycle = CYCLES.find(c => c.id === activeCycle);
  const nbConfigured = (cId) =>
    TYPE_DOCS.filter(td => config[key(cId, td.code)]?.membreId).length;

  return (
    <div>
      <Topbar title="Paramètres — Signataires des documents" subtitle="Configurer le signataire par cycle et par type de document" />
      <div style={{ padding: 28, maxWidth: 960 }}>

        {/* Info box */}
        <div style={{
          background: "rgba(0,168,107,0.07)", border: `1px solid rgba(0,168,107,0.22)`,
          borderRadius: 12, padding: "14px 18px", marginBottom: 24,
          display: "flex", gap: 12, alignItems: "flex-start",
        }}>
          <span style={{ fontSize: 20 }}>ℹ️</span>
          <div style={{ fontSize: 13, color: T.textSecondary, lineHeight: 1.6 }}>
            Chaque cycle a son propre personnel de direction. Désignez ici le responsable dont le nom
            et le titre apparaîtront automatiquement en bas de chaque document officiel généré.
            <br />
            <span style={{ color: T.primary, fontWeight: 600 }}>Si aucun signataire n'est configuré</span>, le nom du directeur de l'établissement (Identité établissement) est utilisé par défaut.
          </div>
        </div>

        {/* ⭐ Onglets par cycle */}
        <div style={{
          background: T.bgCard, border: `1px solid ${T.border}`,
          borderRadius: 16, overflow: "hidden",
        }}>
          {/* Barre d'onglets */}
          <div style={{
            display: "flex", background: T.bgApp,
            borderBottom: `1px solid ${T.border}`,
            overflowX: "auto",
          }}>
            {CYCLES.map(c => {
              const nb = nbConfigured(c.id);
              const isActive = c.id === activeCycle;
              return (
                <div key={c.id} onClick={() => setActiveCycle(c.id)} style={{
                  padding: "14px 24px", cursor: "pointer", flexShrink: 0,
                  fontSize: 14, fontWeight: 500, whiteSpace: "nowrap",
                  color: isActive ? T.primary : T.textSecondary,
                  borderBottom: `2px solid ${isActive ? T.primary : "transparent"}`,
                  display: "flex", alignItems: "center", gap: 8,
                  transition: "all 0.15s ease",
                }}>
                  {c.nom}
                  {/* Compteur signataires configurés */}
                  <span style={{
                    width: 18, height: 18, borderRadius: "50%", fontSize: 10,
                    fontWeight: 700, display: "inline-flex", alignItems: "center", justifyContent: "center",
                    background: nb > 0 ? T.primary : T.textMuted,
                    color: "#fff",
                  }}>{nb}</span>
                </div>
              );
            })}
          </div>

          {/* Panneau actif */}
          <div style={{ padding: 24 }} key={activeCycle}>

            {/* Alerte si aucun personnel */}
            {cycle.personnel.length === 0 && (
              <div style={{
                background: "rgba(220,53,69,0.08)", border: `1px solid rgba(220,53,69,0.25)`,
                borderRadius: 10, padding: "12px 16px", marginBottom: 20,
                fontSize: 13, color: "#FF6B7A",
              }}>
                ⚠️ Aucun membre du personnel n'est inscrit dans le cycle <strong>{cycle.nom}</strong> pour l'année 2025-2026.
                Inscrivez d'abord du personnel avant de configurer les signataires.
              </div>
            )}

            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr>{["Type de document", "Signataire", "Titre honorifique", "Statut"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "8px 14px", fontSize: 11, fontWeight: 600, color: T.textSecondary, textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: `1px solid ${T.border}` }}>{h}</th>
                ))}</tr>
              </thead>
              <tbody>
                {TYPE_DOCS.map((td, i) => {
                  const k = key(cycle.id, td.code);
                  const cur = config[k] || {};
                  const isSaved = saved === k;

                  return (
                    <tr key={td.code} style={{ borderBottom: i < TYPE_DOCS.length - 1 ? `1px solid ${T.border}` : "none" }}>
                      {/* Libellé */}
                      <td style={{ padding: "12px 14px", fontWeight: 500, color: T.textPrimary }}>
                        {td.label}
                        <div style={{ fontSize: 10, fontFamily: T.fontMono, color: T.textMuted, marginTop: 2 }}>{td.code}</div>
                      </td>

                      {/* Dropdown personnel */}
                      <td style={{ padding: "12px 14px", minWidth: 240 }}>
                        {cycle.personnel.length > 0 ? (
                          <select
                            value={cur.membreId || ""}
                            onChange={e => { handleChange(cycle.id, td.code, "membreId", e.target.value); save(cycle.id, td.code); }}
                            style={{
                              width: "100%", background: T.bgInput,
                              border: `1px solid ${cur.membreId ? "rgba(0,168,107,0.40)" : T.border}`,
                              borderRadius: 8, padding: "8px 12px",
                              color: T.textPrimary, fontSize: 13,
                              fontFamily: T.fontInterface,
                            }}
                          >
                            <option value="">— Sélectionner un signataire —</option>
                            {cycle.personnel.map(p => (
                              <option key={p.id} value={p.id}>{p.display}</option>
                            ))}
                          </select>
                        ) : (
                          <span style={{ fontSize: 12, color: T.textMuted, fontStyle: "italic" }}>Aucun personnel disponible</span>
                        )}
                      </td>

                      {/* Titre honorifique */}
                      <td style={{ padding: "12px 14px", minWidth: 180 }}>
                        <input
                          value={cur.titre || ""}
                          onChange={e => handleChange(cycle.id, td.code, "titre", e.target.value)}
                          onBlur={() => save(cycle.id, td.code)}
                          placeholder="Ex : M. le Directeur"
                          disabled={cycle.personnel.length === 0}
                          style={{
                            width: "100%", background: T.bgInput,
                            border: `1px solid ${T.border}`, borderRadius: 8,
                            padding: "8px 12px", color: T.textPrimary, fontSize: 13,
                            fontFamily: T.fontInterface,
                            opacity: cycle.personnel.length === 0 ? 0.4 : 1,
                          }}
                        />
                      </td>

                      {/* Statut */}
                      <td style={{ padding: "12px 14px" }}>
                        {isSaved
                          ? <Badge color="primary">✓ Enregistré</Badge>
                          : cur.membreId
                          ? <Badge color="primary">Configuré</Badge>
                          : <Badge color="neutral">Non configuré</Badge>
                        }
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            <div style={{ marginTop: 20, paddingTop: 16, borderTop: `1px solid ${T.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontSize: 12, color: T.textMuted }}>
                {nbConfigured(cycle.id)} / {TYPE_DOCS.length} types de documents configurés pour le cycle <strong style={{ color: T.textSecondary }}>{cycle.nom}</strong>
              </div>
              <BtnPrimary>✓ Enregistrer toutes les modifications</BtnPrimary>
            </div>
          </div>
        </div>

        {/* ⭐ Aperçu zone signature document */}
        <Card style={{ marginTop: 24 }}>
          <SectionTitle>Aperçu — Zone de signature sur les documents PDF</SectionTitle>
          <div style={{ fontSize: 13, color: T.textMuted, marginBottom: 20 }}>
            Exemple de rendu en bas d'un certificat de scolarité pour le cycle <strong style={{ color: T.textSecondary }}>Secondaire</strong>
          </div>

          {/* Simulation document PDF */}
          <div style={{
            background: "#fff", color: "#1A1A1A", borderRadius: 8,
            padding: "28px 32px", maxWidth: 580,
            fontFamily: "'DejaVu Sans', sans-serif", fontSize: 11,
            boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
          }}>
            {/* En-tête simulé */}
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "2px solid #1B5E20", paddingBottom: 12, marginBottom: 16 }}>
              <div>
                <div style={{ fontWeight: "bold", fontSize: 13 }}>Lycée Municipal de Ouagadougou</div>
                <div style={{ fontSize: 10, color: "#555", marginTop: 3 }}>Ouagadougou, Burkina Faso · Tél : +226 25 30 00 00</div>
                <div style={{ fontSize: 10, color: "#555" }}>N° Agrément MENA : BF/MENA/2019/0042</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontFamily: "monospace", fontSize: 10, color: "#444" }}>CERT-LMO-2026-0090</div>
                <div style={{ width: 50, height: 50, background: "#eee", borderRadius: 4, marginLeft: "auto", marginTop: 4, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 8, color: "#888" }}>QR CODE</div>
              </div>
            </div>
            <div style={{ textAlign: "center", fontWeight: "bold", fontSize: 14, textDecoration: "underline", textTransform: "uppercase", color: "#1B5E20", marginBottom: 20 }}>Certificat de Scolarité</div>
            <p style={{ lineHeight: 1.8, marginBottom: 16, textAlign: "justify" }}>
              Nous soussigné, Proviseur du Lycée Municipal de Ouagadougou, certifions que <strong>DIALLO Ibrahim Junior</strong>,
              né le <strong>15/06/2008</strong> à Ouagadougou, est régulièrement inscrit en classe de <strong>Terminale C</strong>
              pour l'année scolaire <strong>2025-2026</strong> sous le matricule <strong style={{ fontFamily: "monospace" }}>BF-OUA-2025-0187</strong>.
            </p>
            <p style={{ lineHeight: 1.8, textAlign: "justify" }}>
              Ce certificat est délivré à l'intéressé pour servir et valoir ce que de droit.
            </p>

            {/* ⭐ Zone de signature — rendu final */}
            <div style={{ marginTop: 36, textAlign: "right" }}>
              <div style={{ fontSize: 10, color: "#444", marginBottom: 12 }}>Ouagadougou, le 09/03/2026</div>
              <div style={{ fontWeight: "bold", fontSize: 12 }}>M. le Proviseur DIALLO Ibrahim</div>
              <div style={{ fontSize: 10, color: "#555", marginTop: 2, fontStyle: "italic" }}>Proviseur — Cycle Secondaire</div>
              <div style={{ borderBottom: "1px solid #333", width: 160, marginLeft: "auto", marginTop: 28 }} />
              <div style={{ fontSize: 9, color: "#888", marginTop: 4 }}>(Signature et Cachet)</div>
            </div>
          </div>

          <div style={{ marginTop: 16, padding: "12px 14px", background: "rgba(0,168,107,0.06)", border: `1px solid rgba(0,168,107,0.18)`, borderRadius: 10 }}>
            <div style={{ fontSize: 12, color: T.primary, fontWeight: 600, marginBottom: 4 }}>Résolution côté Python (avant génération du PDF) :</div>
            <code style={{ fontSize: 12, fontFamily: T.fontMono, color: T.textSecondary, display: "block", lineHeight: 1.7 }}>
              signataire = SignataireDocument.get_signataire(cycle=secondaire, type_doc="CERT_SCOL", annee=2025-2026)<br/>
              # → titre="M. le Proviseur" | nom="DIALLO" | prenom="Ibrahim"<br/>
              # → poste="Proviseur — Cycle Secondaire"
            </code>
          </div>
        </Card>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// ÉCRAN 6 — PERSONNEL (liste)
// ═══════════════════════════════════════════════════════════════════════════
const PersonnelScreen = () => (
  <div>
    <Topbar title="Gestion du Personnel" subtitle="Année scolaire 2025-2026" />
    <div style={{ padding: 28 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 28 }}>
        <StatCard icon="👩‍🏫" value="52" label="Enseignants" color={T.primary} delay="delay-1" />
        <StatCard icon="🏢" value="18" label="Administratifs" color={T.info} delay="delay-2" />
        <StatCard icon="👔" value="12" label="Direction" color={T.gold} delay="delay-3" />
        <StatCard icon="🔧" value="5" label="Techniques" color="#A259FF" delay="delay-4" />
      </div>
      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div style={{ fontSize: 15, fontWeight: 600 }}>Liste du personnel — 2025-2026</div>
          <div style={{ display: "flex", gap: 10 }}>
            <BtnSecondary small>📄 Exporter PDF</BtnSecondary>
            <BtnPrimary small>+ Enregistrer membre</BtnPrimary>
          </div>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr>{["Matricule", "Nom & Prénom", "Type", "Poste", "Localisation", "Statut"].map(h => (
              <th key={h} style={{ textAlign: "left", padding: "8px 12px", fontSize: 11, fontWeight: 600, color: T.textSecondary, textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: `1px solid ${T.border}` }}>{h}</th>
            ))}</tr>
          </thead>
          <tbody>
            {[
              { mat: "PERS-LMO-2026-0001", nom: "DIALLO Ibrahim", type: "Direction", poste: "Proviseur", loc: "Bureau direction", sc: "primary" },
              { mat: "PERS-LMO-2025-0023", nom: "KINDA Aminata", type: "Direction", poste: "Censeure", loc: "Bureau censure", sc: "primary" },
              { mat: "PERS-LMO-2024-0045", nom: "OUEDRAOGO Karim", type: "Enseignant", poste: "Prof. Mathématiques", loc: "Salle B12", sc: "info" },
              { mat: "PERS-LMO-2023-0012", nom: "SAWADOGO Fatou", type: "Administratif", poste: "Secrétaire principal", loc: "Secrétariat", sc: "neutral" },
            ].map((r, i) => (
              <tr key={i} style={{ borderBottom: `1px solid ${T.border}` }}>
                <td style={{ padding: "11px 12px", fontFamily: T.fontMono, fontSize: 11, color: T.textSecondary }}>{r.mat}</td>
                <td style={{ padding: "11px 12px", fontWeight: 500 }}>{r.nom}</td>
                <td style={{ padding: "11px 12px" }}><Badge color={r.sc}>{r.type}</Badge></td>
                <td style={{ padding: "11px 12px", color: T.textSecondary }}>{r.poste}</td>
                <td style={{ padding: "11px 12px", color: T.textMuted }}>{r.loc}</td>
                <td style={{ padding: "11px 12px" }}><Badge color="primary">Actif</Badge></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ marginTop: 16, paddingTop: 14, borderTop: `1px solid ${T.border}`, display: "flex", gap: 24 }}>
          {[["Total inscrits", "87"], ["Femmes (F)", "34"], ["Hommes (M)", "53"]].map(([lbl, val]) => (
            <div key={lbl} style={{ fontSize: 13 }}>
              <span style={{ color: T.textMuted }}>{lbl} : </span>
              <span style={{ fontWeight: 700, color: T.textPrimary }}>{val}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════
// NAVIGATION HAUT (sélection d'écran)
// ═══════════════════════════════════════════════════════════════════════════
const SCREENS = [
  { id: "dashboard",   label: "🏠 Dashboard",         nav: "dashboard" },
  { id: "eleves",      label: "👤 Enregistrement",    nav: "eleves" },
  { id: "inscription", label: "📋 Inscription",        nav: "inscriptions" },
  { id: "documents",   label: "📄 Documents",          nav: "documents" },
  { id: "signataires", label: "✍️ Signataires ⭐v3.4", nav: "parametres" },
  { id: "personnel",   label: "👨‍🏫 Personnel",          nav: "personnel" },
];

// ═══════════════════════════════════════════════════════════════════════════
// APP ROOT
// ═══════════════════════════════════════════════════════════════════════════
export default function YelenPreview() {
  const [screen, setScreen] = useState("dashboard");
  const [navActive, setNavActive] = useState("dashboard");

  const handleNav = (id) => {
    setNavActive(id);
    const found = SCREENS.find(s => s.nav === id);
    if (found) setScreen(found.id);
  };

  const handleScreen = (id) => {
    const s = SCREENS.find(x => x.id === id);
    setScreen(id);
    if (s) setNavActive(s.nav);
  };

  return (
    <div style={{ fontFamily: T.fontInterface, background: T.bgApp, minHeight: "100vh" }}>
      <style>{G}</style>

      {/* Barre de navigation des écrans (outil développeur) */}
      <div style={{
        position: "fixed", top: 0, left: 240, right: 0, zIndex: 200,
        background: "rgba(10,22,40,0.95)", backdropFilter: "blur(12px)",
        borderBottom: `1px solid ${T.border}`,
        display: "flex", alignItems: "center", gap: 0,
        padding: "0 8px", height: 42,
        overflowX: "auto",
      }}>
        <span style={{ fontSize: 11, color: T.textMuted, marginRight: 12, whiteSpace: "nowrap" }}>ÉCRANS :</span>
        {SCREENS.map(s => (
          <button key={s.id} onClick={() => handleScreen(s.id)} style={{
            padding: "0 14px", height: 42,
            background: screen === s.id ? "rgba(0,168,107,0.15)" : "transparent",
            border: "none", borderBottom: `2px solid ${screen === s.id ? T.primary : "transparent"}`,
            color: screen === s.id ? T.primary : T.textSecondary,
            fontSize: 12, fontWeight: screen === s.id ? 600 : 400,
            cursor: "pointer", whiteSpace: "nowrap",
            fontFamily: T.fontInterface,
          }}>{s.label}</button>
        ))}
      </div>

      <Sidebar active={navActive} onNav={handleNav} />

      {/* Contenu principal */}
      <div style={{ marginLeft: 240, paddingTop: 42 }}>
        {screen === "dashboard"   && <DashboardScreen />}
        {screen === "eleves"      && <EleveScreen />}
        {screen === "inscription" && <InscriptionScreen />}
        {screen === "documents"   && <DocumentsScreen />}
        {screen === "signataires" && <SignatairesScreen />}
        {screen === "personnel"   && <PersonnelScreen />}
      </div>
    </div>
  );
}
