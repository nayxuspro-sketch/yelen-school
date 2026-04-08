/**
 * generate_source_doc.js
 * Génère un document Word professionnel à partir de yelen_source_complet.txt
 *
 * Usage:
 *   node generate_source_doc.js [source.txt] [output.docx]
 *
 * Prérequis:
 *   npm install docx adm-zip
 */

'use strict';

const {
  Document, Packer, Paragraph, TextRun,
  Table, TableRow, TableCell,
  Header, Footer,
  AlignmentType, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageBreak,
} = require('docx');

const fs     = require('fs');
const path   = require('path');
const AdmZip = require('adm-zip');

// ─────────────────────────────────────────────────────────
// CONFIG
// ─────────────────────────────────────────────────────────
const INPUT_FILE  = process.argv[2] || 'yelen_source_complet.txt';
const OUTPUT_FILE = process.argv[3] || 'YELEN_SCHOOL_Code_Source.docx';

const C = {
  primary:    '1A6B3C',
  secondary:  '2D8A5F',
  codeBg:     'F4F4F4',
  borderGray: 'CCCCCC',
  textDark:   '1A1A2E',
  textMuted:  '6B7280',
  white:      'FFFFFF',
  lightGreen: 'E8F5EE',
  totalBg:    'D4EDDA',
};

// ─────────────────────────────────────────────────────────
// PARSING
// ─────────────────────────────────────────────────────────
function parseSourceFile(filePath) {
  if (!fs.existsSync(filePath)) {
    console.error(`Fichier introuvable : ${filePath}`);
    process.exit(1);
  }
  const lines = fs.readFileSync(filePath, 'utf8').split('\n');
  const files = [];
  let currentFile  = null;
  let currentLines = [];

  for (const line of lines) {
    if (/^={10,}$/.test(line) || line.startsWith('===')) continue;
    if (line.startsWith('FICHIER: ') || line.startsWith('### ')) {
      if (currentFile) files.push({ path: currentFile, lines: currentLines });
      currentFile  = line.replace(/^FICHIER:\s*/, '').replace(/^###\s*/, '').trim();
      currentLines = [];
    } else if (currentFile) {
      currentLines.push(line);
    }
  }
  if (currentFile) files.push({ path: currentFile, lines: currentLines });
  return files;
}

function groupByApp(files) {
  const groups = {};
  for (const f of files) {
    const parts = f.path.replace(/^\.[\\/]/, '').replace(/\\/g, '/').split('/');
    let group = 'Racine';
    if (parts[0] === 'apps' && parts.length > 1) group = `apps / ${parts[1]}`;
    else if (parts.length > 1) group = parts[0];
    if (!groups[group]) groups[group] = [];
    groups[group].push(f);
  }
  return groups;
}

// ─────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────
const cellBorder = (color = C.borderGray) => ({
  top:    { style: BorderStyle.SINGLE, size: 1, color },
  bottom: { style: BorderStyle.SINGLE, size: 1, color },
  left:   { style: BorderStyle.SINGLE, size: 1, color },
  right:  { style: BorderStyle.SINGLE, size: 1, color },
});

function spacer(before = 120) {
  return new Paragraph({ children: [new TextRun(' ')], spacing: { before, after: 0 } });
}

function makeCell(text, width, opts = {}) {
  const {
    bold = false, color = C.textDark, fill = C.white,
    align = AlignmentType.LEFT, size = 20, borderColor = C.borderGray,
  } = opts;
  return new TableCell({
    borders: cellBorder(borderColor),
    width: { size: width, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 140, right: 120 },
    children: [new Paragraph({
      alignment: align,
      children: [new TextRun({ text, bold, color, size, font: 'Arial' })],
    })],
  });
}

// ─────────────────────────────────────────────────────────
// PAGE DE GARDE
// ─────────────────────────────────────────────────────────
function buildCoverPage() {
  const today = new Date().toLocaleDateString('fr-FR', {
    day: '2-digit', month: 'long', year: 'numeric',
  });
  const meta = [
    ['Projet',        'YELEN SCHOOL — Gestion Scolaire Burkina Faso'],
    ['Framework',     'Django 4.2 LTS + HTMX + Alpine.js + WeasyPrint'],
    ['Architecture',  '13 applications Django modulaires'],
    ['Version',       'v3.4 — Mars 2026'],
    ['Date export',   today],
    ['Environnement', 'Python 3.11 / PostgreSQL 15 / Redis 7 / Docker'],
  ];

  return [
    spacer(1200),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      shading: { fill: C.primary, type: ShadingType.CLEAR },
      spacing: { before: 100, after: 0 },
      children: [new TextRun({ text: 'YELEN SCHOOL', bold: true, size: 80, color: C.white, font: 'Arial' })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      shading: { fill: C.primary, type: ShadingType.CLEAR },
      spacing: { before: 0, after: 140 },
      children: [new TextRun({ text: 'Systeme de Gestion Scolaire — Burkina Faso', size: 34, color: C.white, font: 'Arial' })],
    }),
    spacer(400),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 180 },
      children: [new TextRun({ text: 'DOCUMENTATION DU CODE SOURCE', bold: true, size: 52, color: C.primary, font: 'Arial' })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 500 },
      children: [new TextRun({ text: 'Annexe Technique — Listing Complet', size: 28, color: C.textMuted, font: 'Arial', italics: true })],
    }),
    new Table({
      width: { size: 8200, type: WidthType.DXA },
      columnWidths: [2800, 5400],
      rows: meta.map(([label, value], i) => new TableRow({ children: [
        makeCell(label, 2800, { bold: true, color: C.primary, fill: i % 2 === 0 ? C.lightGreen : C.white }),
        makeCell(value, 5400, { fill: i % 2 === 0 ? C.white : 'F9FAFB' }),
      ]})),
    }),
    spacer(500),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: '"Illuminer chaque parcours scolaire"', italics: true, size: 24, color: C.textMuted, font: 'Arial' })],
    }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ─────────────────────────────────────────────────────────
// STATISTIQUES
// ─────────────────────────────────────────────────────────
function buildStatsSection(files) {
  const groups     = groupByApp(files);
  const totalLines = files.reduce((s, f) => s + f.lines.length, 0);

  const headerRow = new TableRow({ children: [
    makeCell('Module / Application', 4000, { bold: true, color: C.white, fill: C.primary, borderColor: C.primary }),
    makeCell('Fichiers',             1800, { bold: true, color: C.white, fill: C.primary, borderColor: C.primary, align: AlignmentType.CENTER }),
    makeCell('Lignes de code',       2000, { bold: true, color: C.white, fill: C.primary, borderColor: C.primary, align: AlignmentType.RIGHT }),
  ]});

  const dataRows = Object.entries(groups)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([group, gf], i) => {
      const lns  = gf.reduce((s, f) => s + f.lines.length, 0);
      const fill = i % 2 === 0 ? C.white : 'F9FAFB';
      return new TableRow({ children: [
        makeCell(group,                          4000, { fill }),
        makeCell(String(gf.length),              1800, { fill, align: AlignmentType.CENTER }),
        makeCell(lns.toLocaleString('fr-FR'),    2000, { fill, align: AlignmentType.RIGHT }),
      ]});
    });

  const totalRow = new TableRow({ children: [
    makeCell('TOTAL',                                 4000, { bold: true, color: C.primary, fill: C.totalBg, borderColor: C.primary }),
    makeCell(String(files.length),                   1800, { bold: true, color: C.primary, fill: C.totalBg, borderColor: C.primary, align: AlignmentType.CENTER }),
    makeCell(totalLines.toLocaleString('fr-FR'),     2000, { bold: true, color: C.primary, fill: C.totalBg, borderColor: C.primary, align: AlignmentType.RIGHT }),
  ]});

  return [
    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      shading: { fill: C.primary, type: ShadingType.CLEAR },
      spacing: { before: 200, after: 200 },
      indent: { left: 160 },
      children: [new TextRun({ text: '1. Statistiques du Projet', bold: true, size: 36, color: C.white, font: 'Arial' })],
    }),
    spacer(200),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 300 },
      children: [
        new TextRun({ text: `${files.length} fichiers`, bold: true, size: 30, color: C.primary, font: 'Arial' }),
        new TextRun({ text: '   x   ', size: 30, color: C.textMuted, font: 'Arial' }),
        new TextRun({ text: `${totalLines.toLocaleString('fr-FR')} lignes`, bold: true, size: 30, color: C.primary, font: 'Arial' }),
        new TextRun({ text: '   x   ', size: 30, color: C.textMuted, font: 'Arial' }),
        new TextRun({ text: `${Object.keys(groups).length} modules`, bold: true, size: 30, color: C.primary, font: 'Arial' }),
      ],
    }),
    new Table({
      width: { size: 7800, type: WidthType.DXA },
      columnWidths: [4000, 1800, 2000],
      rows: [headerRow, ...dataRows, totalRow],
    }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ─────────────────────────────────────────────────────────
// CODE SOURCE PAR MODULE
// ─────────────────────────────────────────────────────────
function buildCodeSections(files) {
  const groups   = groupByApp(files);
  const children = [];
  let   secNum   = 2;

  for (const [group, groupFiles] of Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0]))) {
    children.push(new Paragraph({
      heading: HeadingLevel.HEADING_1,
      shading: { fill: C.primary, type: ShadingType.CLEAR },
      spacing: { before: 200, after: 200 },
      indent: { left: 160 },
      children: [new TextRun({ text: `${secNum}. ${group}`, bold: true, size: 36, color: C.white, font: 'Arial' })],
    }));
    secNum++;

    for (const file of groupFiles) {
      const fileName = path.basename(file.path).replace(/\\/g, '/');
      const dirName  = path.dirname(file.path).replace(/\\/g, '/');

      children.push(new Paragraph({
        heading: HeadingLevel.HEADING_3,
        shading: { fill: C.lightGreen, type: ShadingType.CLEAR },
        spacing: { before: 280, after: 80 },
        indent: { left: 120 },
        children: [
          new TextRun({ text: fileName, bold: true, color: C.secondary, size: 24, font: 'Courier New' }),
          new TextRun({ text: `   ${dirName}`, color: C.textMuted, size: 18, font: 'Arial' }),
        ],
      }));

      if (file.lines.length === 0) {
        children.push(new Paragraph({
          shading: { fill: C.codeBg, type: ShadingType.CLEAR },
          indent: { left: 360 },
          children: [new TextRun({ text: '(fichier vide)', italics: true, color: C.textMuted, size: 18, font: 'Arial' })],
        }));
      } else {
        for (const line of file.lines) {
          const text = line.length > 120 ? line.substring(0, 117) + '...' : line;
          children.push(new Paragraph({
            shading: { fill: C.codeBg, type: ShadingType.CLEAR },
            spacing: { before: 0, after: 0, line: 220 },
            indent: { left: 360, right: 360 },
            children: [new TextRun({ text: text || ' ', font: 'Courier New', size: 16, color: C.textDark })],
          }));
        }
      }
      children.push(spacer(180));
    }
    children.push(new Paragraph({ children: [new PageBreak()] }));
  }
  return children;
}

// ─────────────────────────────────────────────────────────
// EN-TETE
// ─────────────────────────────────────────────────────────
function buildHeader() {
  return {
    default: new Header({
      children: [new Paragraph({
        spacing: { after: 100 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.primary, space: 2 } },
        children: [
          new TextRun({ text: 'YELEN SCHOOL', bold: true, size: 20, color: C.primary, font: 'Arial' }),
          new TextRun({ text: '  -  Documentation Code Source', size: 18, color: C.textMuted, font: 'Arial' }),
        ],
      })],
    }),
  };
}

// ─────────────────────────────────────────────────────────
// PIED DE PAGE — marqueur PAGENUM remplace apres via XML
// ─────────────────────────────────────────────────────────
function buildFooter() {
  return {
    default: new Footer({
      children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 80 },
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: C.borderGray, space: 2 } },
        children: [
          new TextRun({ text: 'Confidentiel - Usage interne  |  Page ', size: 16, color: C.textMuted, font: 'Arial' }),
          new TextRun({ text: 'PAGENUM', size: 16, color: C.textMuted, font: 'Arial' }),
          new TextRun({ text: '  |  Burkina Faso', size: 16, color: C.textMuted, font: 'Arial' }),
        ],
      })],
    }),
  };
}

// ─────────────────────────────────────────────────────────
// INJECTION DU NUMERO DE PAGE DANS LE FOOTER VIA XML
// Remplace le run <w:t>PAGENUM</w:t> par un champ PAGE Word valide
// ─────────────────────────────────────────────────────────
function injectPageNumber(docxPath) {
  const zip   = new AdmZip(docxPath);
  const entry = zip.getEntry('word/footer1.xml');
  if (!entry) {
    console.warn('  footer1.xml introuvable, numero de page non injecte.');
    return;
  }

  let xml = zip.readAsText(entry);

  const rPr = [
    '<w:rPr>',
    '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>',
    '<w:color w:val="6B7280"/>',
    '<w:sz w:val="16"/>',
    '<w:szCs w:val="16"/>',
    '</w:rPr>',
  ].join('');

  const pageField = [
    `<w:r>${rPr}<w:fldChar w:fldCharType="begin"/></w:r>`,
    `<w:r>${rPr}<w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>`,
    `<w:r>${rPr}<w:fldChar w:fldCharType="separate"/></w:r>`,
    `<w:r>${rPr}<w:t>1</w:t></w:r>`,
    `<w:r>${rPr}<w:fldChar w:fldCharType="end"/></w:r>`,
  ].join('');

  // Remplace le run contenant PAGENUM
  const before = xml.indexOf(">PAGENUM</w:t>");
  if (before === -1) {
    console.warn('  Marqueur PAGENUM non trouve dans le footer.');
    return;
  }

  // Retrouver le debut du <w:r> englobant
  const runStart = xml.lastIndexOf('<w:r>', before);
  const runEnd   = xml.indexOf('</w:r>', before) + '</w:r>'.length;

  xml = xml.substring(0, runStart) + pageField + xml.substring(runEnd);

  zip.updateFile('word/footer1.xml', Buffer.from(xml, 'utf8'));
  zip.writeZip(docxPath);
  console.log('  Numero de page injecte avec succes.');
}

// ─────────────────────────────────────────────────────────
// MAIN
// ─────────────────────────────────────────────────────────
async function main() {
  console.log(`\nLecture de ${INPUT_FILE}...`);
  const files = parseSourceFile(INPUT_FILE);
  console.log(`${files.length} fichiers detectes`);

  const groups = groupByApp(files);
  console.log(`${Object.keys(groups).length} modules trouves`);

  const children = [
    ...buildCoverPage(),
    ...buildStatsSection(files),
    ...buildCodeSections(files),
  ];

  const doc = new Document({
    title:       'YELEN SCHOOL - Code Source Complet',
    subject:     'Documentation Technique',
    creator:     'YELEN SCHOOL Generator',
    description: 'Listing complet du code source',
    styles: {
      default: {
        document: { run: { font: 'Arial', size: 20, color: C.textDark } },
      },
      paragraphStyles: [
        { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { size: 36, bold: true, font: 'Arial', color: C.white },
          paragraph: { spacing: { before: 200, after: 200 }, outlineLevel: 0 } },
        { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { size: 28, bold: true, font: 'Arial', color: C.primary },
          paragraph: { spacing: { before: 320, after: 120 }, outlineLevel: 1 } },
        { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { size: 24, bold: true, font: 'Arial', color: C.secondary },
          paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 2 } },
      ],
    },
    sections: [{
      properties: {
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1000, right: 1000, bottom: 1000, left: 1200 },
        },
      },
      headers: buildHeader(),
      footers: buildFooter(),
      children,
    }],
  });

  console.log('Generation du document Word...');
  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(OUTPUT_FILE, buffer);
  console.log(`Taille initiale : ${(buffer.length / 1024).toFixed(1)} Ko`);

  injectPageNumber(OUTPUT_FILE);

  const finalSize = fs.statSync(OUTPUT_FILE).size;
  console.log(`\nDocument pret : ${OUTPUT_FILE}`);
  console.log(`Taille finale : ${(finalSize / 1024).toFixed(1)} Ko`);
}

main().catch(err => {
  console.error('Erreur :', err.message);
  process.exit(1);
});
