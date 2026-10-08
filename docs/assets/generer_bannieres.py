"""Génère la cover GitHub (1280x640) et les bandeaux de section du README, aux couleurs du concept Tableau.

Les polices de l'appli sont sous-ensemblées et incluses dans chaque SVG, pour un rendu identique sur GitHub.
Usage : python docs/assets/generer_bannieres.py . docs/assets  (demande fonttools et brotli)
"""
import base64, io, re, sys
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont

REPO = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
FONTS = REPO / "chat/static/learny/fonts"

ICONS = {
    "math": '<path d="M18 5H7l6 7-6 7h11"/>',
    "flask": '<path d="M9 3h6M10 3v6L4.5 19a1.3 1.3 0 0 0 1.1 2h12.8a1.3 1.3 0 0 0 1.1-2L14 9V3M7 15h10"/>',
    "leaf": '<path d="M5 19c0-8 5-14 15-14 0 10-6 15-14 15M5 19l7-7"/>',
    "mic": '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    "offline": '<path d="M3 3l18 18M8.5 16.5a5 5 0 0 1 7 0M5 13a10 10 0 0 1 4-2.4M19 13a10 10 0 0 0-2-1.5M2 9.5a15 15 0 0 1 4.3-2.8M22 9.5A15 15 0 0 0 11 5.1M12 20h.01"/>',
    "send": '<path d="M5 12h13M12 5l7 7-7 7"/>',
    "book": '<path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H20v15H5.5A1.5 1.5 0 0 0 4 19.5z"/><path d="M4 19.5A1.5 1.5 0 0 0 5.5 21H20v-3"/>',
}


def icon(name, x, y, size, color, sw=2):
    s = size / 24
    return (f'<g transform="translate({x} {y}) scale({s})" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>')


def robot(x, y, size, body="#146B43", line="#F3F6F2", accent="#F2C14E", tile=True):
    """Icône Learny (chat/static/learny/img/icone.svg) placée en (x, y)."""
    s = size / 512
    bg = f'<rect width="512" height="512" rx="112" fill="{body}"/>' if tile else ""
    return (f'<g transform="translate({x} {y}) scale({s})">{bg}'
            f'<rect x="128" y="176" width="256" height="200" rx="64" fill="none" stroke="{line}" stroke-width="28"/>'
            f'<path d="M256 176v-52" stroke="{line}" stroke-width="28" stroke-linecap="round"/>'
            f'<circle cx="256" cy="112" r="20" fill="{accent}"/>'
            f'<path d="M208 256v20M304 256v20" stroke="{line}" stroke-width="28" stroke-linecap="round"/>'
            f'<path d="M216 322h80" stroke="{accent}" stroke-width="24" stroke-linecap="round"/></g>')


def font_face(svg_body):
    texts = "".join(re.findall(r">([^<>]+)<", svg_body))
    texts = re.sub(r"&[a-z]+;", "", texts) + "0123456789 "
    css = []
    for fam, file, weight in [
        ("Atkinson Hyperlegible", "atkinson-hyperlegible-latin-400-normal.woff2", 400),
        ("Atkinson Hyperlegible", "atkinson-hyperlegible-latin-700-normal.woff2", 700),
        ("Bricolage Grotesque", "bricolage-grotesque-latin-700-normal.woff2", 700),
    ]:
        font = TTFont(FONTS / file)
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern", "liga"]
        sub = subset.Subsetter(opts)
        sub.populate(text=texts)
        sub.subset(font)
        buf = io.BytesIO()
        font.flavor = "woff2"
        font.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        css.append(f"@font-face{{font-family:'{fam}';font-weight:{weight};src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    return "".join(css)


def write(name, title, body, w=1280, h=640):
    style = font_face(body) + (
        ".d{font-family:'Bricolage Grotesque','Atkinson Hyperlegible',sans-serif;font-weight:700}"
        ".b{font-family:'Atkinson Hyperlegible',sans-serif}.bb{font-family:'Atkinson Hyperlegible',sans-serif;font-weight:700}")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
           f'aria-labelledby="t"><title id="t">{title}</title><style>{style}</style>{body}</svg>')
    (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
    print(name, len(svg) // 1024, "ko")


CHALK_FILTER = """<filter id="craie" x="-5%" y="-5%" width="110%" height="110%">
<feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3" result="n"/>
<feDisplacementMap in="SourceGraphic" in2="n" scale="2.2"/></filter>"""

BOARD_DEFS = """<radialGradient id="tache1" cx="0.3" cy="0.35" r="0.6"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".07"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></radialGradient>
<radialGradient id="tache2" cx="0.8" cy="0.7" r="0.5"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".05"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></radialGradient>
<linearGradient id="ardoise" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#17583A"/><stop offset="1" stop-color="#0E3F27"/></linearGradient>
<pattern id="grille" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#FFFFFF" stroke-opacity=".045"/></pattern>"""


# ---------------------------------------------------------------- A · Ardoise
def cover_a():
    W, H = 1280, 640
    chalk = "#EDF3EE"
    b = [f"<defs>{BOARD_DEFS}{CHALK_FILTER}</defs>",
         f'<rect width="{W}" height="{H}" fill="#6B4A2B"/>',  # cadre bois
         f'<rect x="6" y="6" width="{W-12}" height="{H-12}" rx="4" fill="#8A6239"/>',
         f'<rect x="22" y="22" width="{W-44}" height="{H-70}" rx="6" fill="url(#ardoise)"/>',
         f'<rect x="22" y="22" width="{W-44}" height="{H-70}" rx="6" fill="url(#grille)"/>',
         f'<rect x="22" y="22" width="{W-44}" height="{H-70}" fill="url(#tache1)"/>',
         f'<rect x="22" y="22" width="{W-44}" height="{H-70}" fill="url(#tache2)"/>',
         # rebord à craie
         f'<rect x="0" y="{H-48}" width="{W}" height="48" fill="#5A3D22"/>',
         f'<rect x="0" y="{H-48}" width="{W}" height="6" fill="#7A5634"/>',
         f'<rect x="980" y="{H-40}" width="70" height="16" rx="7" fill="#F2C14E"/>',
         f'<rect x="1066" y="{H-38}" width="46" height="14" rx="6" fill="#F3F6F2"/>',
         f'<rect x="1126" y="{H-42}" width="80" height="22" rx="4" fill="#3A2A1A"/>',  # brosse
         f'<rect x="1126" y="{H-42}" width="80" height="8" rx="3" fill="#A88A63"/>',
         ]
    g = ['<g filter="url(#craie)">']
    g.append(robot(84, 92, 132, body="none", line=chalk, accent="#F2C14E", tile=False))
    g.append(f'<text x="236" y="196" font-size="128" class="d" fill="{chalk}" letter-spacing="-3">Learny</text>')
    g.append('<path d="M242 222 C 340 210, 470 232, 640 214" fill="none" stroke="#F2C14E" stroke-width="7" stroke-linecap="round"/>')
    g.append(f'<text x="92" y="318" font-size="40" class="bb" fill="{chalk}">Le répétiteur du BEPC</text>')
    g.append(f'<text x="92" y="368" font-size="40" class="b" fill="#C9DCCF">dans la poche des élèves de 3e.</text>')
    # matières
    x = 92
    for ic, label, wdt in [("math", "Maths", 168), ("flask", "Physique-chimie", 288), ("leaf", "SVT", 140)]:
        g.append(f'<rect x="{x}" y="420" width="{wdt}" height="60" rx="30" fill="none" stroke="{chalk}" stroke-opacity=".8" stroke-width="2.5"/>')
        g.append(icon(ic, x + 22, 436, 28, "#F2C14E", 2.2))
        g.append(f'<text x="{x+62}" y="460" font-size="27" class="b" fill="{chalk}">{label}</text>')
        x += wdt + 18
    g.append(f'<text x="92" y="540" font-size="24" class="b" fill="#F2C14E">Burkina Faso · Programme officiel de 3e · Gemini</text>')
    # griffonnages à droite
    g.append(f'<g opacity=".55" fill="{chalk}">')
    g.append(f'<text x="880" y="120" font-size="38" class="b" transform="rotate(-6 880 120)">x² + 3x = 0</text>')
    g.append(f'<text x="905" y="178" font-size="30" class="b" transform="rotate(-6 905 178)">x(x + 3) = 0</text>')
    g.append('<path d="M890 196 l210 -22" stroke="#EDF3EE" stroke-width="2"/>')
    g.append('</g>')
    # triangle rectangle
    g.append('<g opacity=".6" fill="none" stroke="#EDF3EE" stroke-width="3" stroke-linejoin="round">'
             '<path d="M930 470 L930 270 L1180 470 Z"/><path d="M930 444 h26 v26"/></g>')
    g.append(f'<g opacity=".6" fill="{chalk}"><text x="900" y="378" font-size="28" class="b">a</text>'
             f'<text x="1046" y="506" font-size="28" class="b">b</text><text x="1070" y="356" font-size="28" class="b">c</text>'
             f'<text x="980" y="550" font-size="32" class="bb" fill="#F2C14E">a² + b² = c²</text></g>')
    g.append('</g>')
    write("cover-a-ardoise", "Learny, le répétiteur du BEPC : cover version ardoise", "".join(b + g))


cover_a()


# ---------------------------------------------------------------- Bandeaux de section
ICONS["layers"] = '<path d="M12 3 3 8l9 5 9-5zM3 13l9 5 9-5"/>'
ICONS["rocket"] = '<path d="M5 15c-1.5 1.5-2 4-2 6 2 0 4.5-.5 6-2M9 15l-3-3c1-4 4-8 11-9-1 7-5 10-9 11zM14.5 9.5h.01"/>'
ICONS["server"] = '<rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 7.5h.01M7 16.5h.01"/>'
ICONS["spark"] = '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>'
ICONS["eye"] = '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>'


def bandeau(slug, num, titre, sous, ic, deco):
    W, H = 1280, 120
    b = [f"<defs>{BOARD_DEFS}<clipPath id='c'><rect width='{W}' height='{H}' rx='18'/></clipPath></defs>",
         "<g clip-path='url(#c)'>",
         f'<rect width="{W}" height="{H}" fill="url(#ardoise)"/>',
         f'<rect width="{W}" height="{H}" fill="url(#grille)"/>',
         f'<rect width="{W}" height="{H}" fill="url(#tache1)"/>',
         f'<rect x="0" y="0" width="10" height="{H}" fill="#F2C14E"/>',
         f'<text x="44" y="78" font-size="44" class="d" fill="#F2C14E">{num}</text>',
         f'<rect x="124" y="30" width="60" height="60" rx="16" fill="#F3F6F2" fill-opacity=".1"/>',
         icon(ic, 138, 44, 32, "#F3F6F2", 2),
         f'<text x="206" y="66" font-size="38" class="d" fill="#F3F6F2" letter-spacing="-.5">{titre}</text>',
         f'<text x="208" y="96" font-size="20" class="b" fill="#C9DCCF">{sous}</text>',
         f'<text x="1236" y="76" font-size="34" class="b" fill="#EDF3EE" fill-opacity=".35" text-anchor="end">{deco}</text>',
         "</g>"]
    write(f"section-{slug}", f"{titre} : {sous}", "".join(b), W, H)


bandeau("fonctionnalites", "01", "Fonctionnalités", "Ce que Learny fait pour l'élève", "spark", "x² + 3x = 0")
bandeau("accessibilite", "02", "Accessibilité", "Pensé pour tous les élèves, sur tous les téléphones", "eye", "a² + b² = c²")
bandeau("architecture", "03", "Architecture", "Django, htmx et Gemini, sans tâche de fond", "layers", "y = ax + b")
bandeau("demarrer", "04", "Démarrer en local", "De zéro à la première question en cinq commandes", "rocket", "(a + b)²")
bandeau("deployer", "05", "Déployer sur o2switch", "Hébergement mutualisé cPanel et PostgreSQL", "server", "b² - 4ac")
