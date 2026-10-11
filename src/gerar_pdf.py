import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, Paragraph, Preformatted, SimpleDocTemplate,
                                Spacer, Table, TableStyle, KeepTogether)

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FONTES = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", FONTES + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DV-B", FONTES + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DV-I", FONTES + "DejaVuSans-Oblique.ttf"))
pdfmetrics.registerFont(TTFont("DVM", FONTES + "DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-B")

H1 = ParagraphStyle("h1", fontName="DV-B", fontSize=17, leading=21, spaceAfter=8, textColor=colors.HexColor("#14532d"))
H2 = ParagraphStyle("h2", fontName="DV-B", fontSize=13, leading=17, spaceBefore=12, spaceAfter=5, keepWithNext=1, textColor=colors.HexColor("#14532d"))
H3 = ParagraphStyle("h3", fontName="DV-B", fontSize=10.5, leading=14, spaceBefore=8, spaceAfter=3, keepWithNext=1)
P = ParagraphStyle("p", fontName="DV", fontSize=9, leading=12.8, spaceAfter=5)
LI = ParagraphStyle("li", parent=P, leftIndent=12, bulletIndent=2, spaceAfter=2)
CELL = ParagraphStyle("cell", fontName="DV", fontSize=7.6, leading=9.8)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="DV-B", textColor=colors.white)
COD = ParagraphStyle("cod", fontName="DVM", fontSize=6.8, leading=8.4, backColor=colors.HexColor("#f3f4f6"),
                     borderPadding=4, spaceAfter=6)


def inline(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r'<font name="DVM" size="8">\1</font>', t)
    t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", t)
    return t


def tabela(linhas, larg):
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in linhas
            if not re.match(r"^\s*\|[\s\-:|]+\|\s*$", l)]
    n = len(rows[0])
    data = [[Paragraph(inline(c), CELLB if i == 0 else CELL) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[larg / n] * n, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14532d")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9ca3af")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0fdf4")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def imagem(caminho, larg):
    from PIL import Image as PI
    w, h = PI.open(caminho).size
    maxh = 17 * cm
    esc = min(larg / w, maxh / h)
    return Image(caminho, width=w * esc, height=h * esc)


def construir(saida):
    doc = SimpleDocTemplate(saida, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title="ChargeGrid Intelligence - Sprint 3", author="1CCPH - Equipe 1")
    larg = A4[0] - 4 * cm
    linhas = open(os.path.join(RAIZ, "README.md"), encoding="utf-8").read().split("\n")
    fl, i = [], 0
    while i < len(linhas):
        l = linhas[i]
        if l.startswith("```"):
            i += 1
            bloco = []
            while not linhas[i].startswith("```"):
                bloco.append(linhas[i])
                i += 1
            texto = "\n".join(bloco)
            # quebra linhas longas para caber na página
            quebradas = []
            for b in texto.split("\n"):
                while len(b) > 120:
                    quebradas.append(b[:120])
                    b = "    " + b[120:]
                quebradas.append(b)
            fl.append(Preformatted("\n".join(quebradas), COD))
        elif l.startswith("# "):
            fl.append(Paragraph(inline(l[2:]), H1))
        elif l.startswith("## "):
            fl.append(Paragraph(inline(l[3:]), H2))
        elif l.startswith("### "):
            fl.append(Paragraph(inline(l[4:]), H3))
        elif l.startswith("|"):
            bloco = []
            while i < len(linhas) and linhas[i].startswith("|"):
                bloco.append(linhas[i])
                i += 1
            fl.append(tabela(bloco, larg))
            fl.append(Spacer(1, 6))
            continue
        elif l.startswith("!["):
            m = re.match(r"!\[(.*?)\]\((.*?)\)", l)
            fl.append(KeepTogether([imagem(os.path.join(RAIZ, m.group(2)), larg),
                                    Paragraph(f"<i>{inline(m.group(1))}</i>", ParagraphStyle("c", parent=P, alignment=1, fontSize=7.5))]))
        elif l.startswith("- "):
            fl.append(Paragraph(inline(l[2:]), LI, bulletText="•"))
        elif l.strip():
            fl.append(Paragraph(inline(l), P))
        i += 1

    def rodape(c, d):
        c.setFont("DV", 7)
        c.setFillColor(colors.grey)
        c.drawString(2 * cm, 1 * cm, "ChargeGrid Intelligence - Sprint 3 - 1CCPH Equipe 1")
        c.drawRightString(A4[0] - 2 * cm, 1 * cm, f"pág. {d.page}")
    doc.build(fl, onFirstPage=rodape, onLaterPages=rodape)


if __name__ == "__main__":
    out = os.path.join(RAIZ, "docs", "ChargeGrid_Sprint3.pdf")
    construir(out)
    print("PDF gerado:", out)
