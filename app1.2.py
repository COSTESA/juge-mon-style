"""
╔══════════════════════════════════════════════════════════════════╗
║          ✦  JUGE MON STYLE  —  app.py                           ║
║   Analyse vestimentaire IA · Premium · Smart Friend             ║
╚══════════════════════════════════════════════════════════════════╝

Changelog v1.4 :
  - [FIX]     Bug HTML Mode Dilemme : fuite de balises dans st.markdown corrigée
               en sortant les expressions conditionnelles des f-strings imbriquées.
  - [FEATURE] Analyses plus détaillées : prompts mis à jour pour 5-6 phrases riches
               qui exploitent le raisonnement privé <reflexion>.
  - [FEATURE] Rate Limiting : 3 analyses gratuites par jour via st.session_state
               (clé `analyses_today` + `last_analysis_date`). Roast non limité.
  - [FEATURE] Bouton "Générer ma Story" : génération d'une image 1080×1920 px
               (format 9:16) avec Pillow + st.download_button.
"""

# ─── IMPORTS ──────────────────────────────────────────────────────────────────
import io
import re
import base64
import textwrap
from datetime import date

import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from openai import OpenAI


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 0 — CONFIG PAGE
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Juge Mon Style",
    page_icon="✦",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════

STRIPE_LINK = "https://buy.stripe.com/test_14A00i1Qhcox7nI9qV77O00"
# Stripe : URL de confirmation → https://ton-app.streamlit.app/?payment=success

# ── Limite d'analyses gratuites par jour ──────────────────────────────────────
MAX_ANALYSES_PAR_JOUR = 3

SITUATIONS = [
    # ── Quotidien & détente ────────────────────────────────────────────────────
    {"emoji": "🛋️", "label": "Journée chill",
     "desc": "une journée à traîner, se reposer ou rester à la maison — le confort prime absolument, mais ça ne veut pas dire n'importe quoi"},
    {"emoji": "🛒", "label": "Faire les courses",
     "desc": "une sortie courses ou petite course du quotidien — tenue pratique, décontractée, sans effort visible mais pas négligée"},
    {"emoji": "📚", "label": "Cours / Études",
     "desc": "une journée de cours ou d'études — tenue décontractée, fonctionnelle, qui permet de rester concentré toute la journée"},
    {"emoji": "☕", "label": "Café / Balade",
     "desc": "un café entre amis ou une balade en ville — casual et soigné, le bon équilibre entre confort et style au quotidien"},
    {"emoji": "🏋️", "label": "Sport / Loisirs",
     "desc": "une session sport ou activité de loisirs — performance et esthétique athlétique"},
    {"emoji": "⛺", "label": "Week-end outdoor",
     "desc": "un week-end nature, randonnée ou camping — fonctionnel mais pas négligé"},
    # ── Occasions sociales ────────────────────────────────────────────────────
    {"emoji": "🍽️", "label": "Repas de famille",
     "desc": "un repas dominical en famille — entre confort et tenue, ni trop décontracté ni trop guindé"},
    {"emoji": "🎪", "label": "Festival",
     "desc": "un festival de musique en plein air — liberté créative maximale, confort essentiel, et tout le monde est là pour se montrer"},
    {"emoji": "🎧", "label": "Soirée / Club",
     "desc": "une soirée en club ou bar — style affirmé, à l'aise dans le mouvement, avec une vraie personnalité"},
    # ── Enjeux forts ──────────────────────────────────────────────────────────
    {"emoji": "💒", "label": "Mariage (invité)",
     "desc": "un mariage en tant qu'invité — élégance requise, sans voler la vedette aux mariés"},
    {"emoji": "🥂", "label": "Soirée chic",
     "desc": "une soirée habillée ou un dîner élégant — l'occasion de monter en gamme sans tomber dans l'excès"},
    {"emoji": "💘", "label": "Premier rendez-vous",
     "desc": "un premier rendez-vous romantique — la première impression compte énormément, il faut paraître soigné, accessible et soi-même"},
    {"emoji": "💼", "label": "Entretien d'embauche",
     "desc": "un entretien d'embauche dans une entreprise parisienne — crédibilité, compétence et discrétion sont les maîtres-mots"},
]

SITUATION_LABELS = [f"{s['emoji']} {s['label']}" for s in SITUATIONS]

AFFILIATE_CATALOG = {
    # ── Bijoux & accessoires ─────────────────────────────────────────────────
    "bague_chunky": {
        "name": "Bague chunky statement",
        "emoji": "◈",
        "tagline": "Le détail qui parle avant toi",
        "affiliate_url": "https://www.example.com/bague-chunky?ref=monstyliste",
    },
    "collier_perles_y2k": {
        "name": "Collier de perles Y2K",
        "emoji": "✦",
        "tagline": "Coucou 2003, ravie de te revoir",
        "affiliate_url": "https://www.example.com/collier-perles?ref=monstyliste",
    },
    "bracelet_manchette": {
        "name": "Bracelet manchette doré",
        "emoji": "◯",
        "tagline": "Une pièce, tout le caractère",
        "affiliate_url": "https://www.example.com/manchette?ref=monstyliste",
    },
    # ── Lunettes ─────────────────────────────────────────────────────────────
    "lunettes_y2k": {
        "name": "Lunettes teintées Y2K",
        "emoji": "◉",
        "tagline": "Le filtre soleil qui clôt tout débat",
        "affiliate_url": "https://www.example.com/lunettes-y2k?ref=monstyliste",
    },
    "lunettes_cat_eye": {
        "name": "Lunettes cat-eye vintage",
        "emoji": "◉",
        "tagline": "Drama facial instantané",
        "affiliate_url": "https://www.example.com/cat-eye?ref=monstyliste",
    },
    # ── Chaussures ───────────────────────────────────────────────────────────
    "sneakers_vintage": {
        "name": "Sneakers running vintage",
        "emoji": "△",
        "tagline": "La base qui élève tout le reste",
        "affiliate_url": "https://www.example.com/sneakers-vintage?ref=monstyliste",
    },
    "mary_janes": {
        "name": "Mary Janes chunky",
        "emoji": "△",
        "tagline": "Douceur en dessous, impact au-dessus",
        "affiliate_url": "https://www.example.com/mary-janes?ref=monstyliste",
    },
    "boots_chelsea": {
        "name": "Chelsea boots cuir",
        "emoji": "△",
        "tagline": "La chaussure qui structure une silhouette",
        "affiliate_url": "https://www.example.com/chelsea-boots?ref=monstyliste",
    },
    # ── Vestes & couches ─────────────────────────────────────────────────────
    "veste_gorpcore": {
        "name": "Veste Gorpcore technique",
        "emoji": "□",
        "tagline": "Quand la randonnée devient un esthétique",
        "affiliate_url": "https://www.example.com/veste-gorpcore?ref=monstyliste",
    },
    "veste_oversize": {
        "name": "Veste blazer oversize",
        "emoji": "□",
        "tagline": "La pièce qui structure toute la silhouette",
        "affiliate_url": "https://www.example.com/veste-oversize?ref=monstyliste",
    },
    "cardigan_knit": {
        "name": "Cardigan knit texturé",
        "emoji": "□",
        "tagline": "Le confort qui n'abandonne pas le style",
        "affiliate_url": "https://www.example.com/cardigan-knit?ref=monstyliste",
    },
    # ── Sacs ─────────────────────────────────────────────────────────────────
    "sac_hobo": {
        "name": "Sac hobo en cuir souple",
        "emoji": "◇",
        "tagline": "Structure molle, impact maximal",
        "affiliate_url": "https://www.example.com/sac-hobo?ref=monstyliste",
    },
    "micro_bag": {
        "name": "Micro bag minimaliste",
        "emoji": "◇",
        "tagline": "Moins c'est plus — surtout ici",
        "affiliate_url": "https://www.example.com/micro-bag?ref=monstyliste",
    },
    "sac_tote_canvas": {
        "name": "Tote bag canvas premium",
        "emoji": "◇",
        "tagline": "Sobre, utile et infiniment stylé",
        "affiliate_url": "https://www.example.com/tote-canvas?ref=monstyliste",
    },
    # ── Headwear & divers ─────────────────────────────────────────────────────
    "casquette_trucker": {
        "name": "Casquette trucker rétro",
        "emoji": "△",
        "tagline": "Un clin d'œil qui change tout",
        "affiliate_url": "https://www.example.com/trucker-cap?ref=monstyliste",
    },
    "bandeau_satin": {
        "name": "Bandeau satin imprimé",
        "emoji": "✦",
        "tagline": "Mini accessoire, maxi effet",
        "affiliate_url": "https://www.example.com/bandeau-satin?ref=monstyliste",
    },
    "ceinture_large": {
        "name": "Ceinture large à boucle dorée",
        "emoji": "◈",
        "tagline": "Définit la taille, redéfinit la tenue",
        "affiliate_url": "https://www.example.com/ceinture-large?ref=monstyliste",
    },
}

_CATALOG_LINES = "\n".join(
    f"  - {k} → {v['name']}" for k, v in AFFILIATE_CATALOG.items()
)
_CATALOG_KEYS = ", ".join(AFFILIATE_CATALOG.keys())


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — CLIENT OPENAI
# ══════════════════════════════════════════════════════════════════════════════

try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.error("⚠️ Clé API introuvable — vérifiez `.streamlit/secrets.toml` (clé : OPENAI_API_KEY).")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════

def compress_image_to_base64(pil_image, max_dimension=768, quality=80):
    """
    Prépare l'image. Dimension réduite à 768px pour diviser le coût des tokens
    en input par 2, tout en gardant la qualité nécessaire pour le détail des matières.
    Coût estimé ~765 tokens/image (vs 85 en low) — justifié pour l'analyse premium.
    """
    img = pil_image.copy()
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > max_dimension:
        ratio = max_dimension / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def _build_image_block(b64: str) -> dict:
    """Construit le bloc image OpenAI avec detail=auto (optimisation intelligente coût/qualité)."""
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{b64}",
            "detail": "auto",
        },
    }


def appeler_openai(prompt: str, images_b64: list) -> str:
    """
    Envoie le prompt + 1 ou 2 images à OpenAI Vision.
    images_b64 : liste de strings base64 (1 = analyse classique, 2 = dilemme A/B).
    detail=auto : OpenAI choisit intelligemment low ou high selon la taille de l'image.
    """
    content = [{"type": "text", "text": prompt}]
    for b64 in images_b64:
        content.append(_build_image_block(b64))

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1200,  # Augmenté pour les analyses plus détaillées
        messages=[{"role": "user", "content": content}],
    )
    return response.choices[0].message.content


def extraire_reflexion(reponse_brute: str) -> tuple:
    """Extrait le bloc <reflexion>…</reflexion>. Retourne (reflexion, reponse_propre)."""
    pattern = re.compile(r"<reflexion>(.*?)</reflexion>", re.DOTALL | re.IGNORECASE)
    match = pattern.search(reponse_brute)
    reflexion_text = match.group(1).strip() if match else ""
    reponse_propre = pattern.sub("", reponse_brute).strip()
    return reflexion_text, reponse_propre


def parser_reponse(reponse_propre: str) -> dict:
    """
    Parse le format pipe commun à tous les modes.

    Analyse classique (8 champs) :
      visibilite | genre | description | score | titre | analyse | conseil | accessoire

    Mode Dilemme (9 champs) :
      visibilite | genre | desc_a | desc_b | gagnante | score_a | score_b | analyse_comparative | accessoire

    Mode Roast (7 champs) :
      visibilite | genre | description | score | titre | roast | punchline
    """
    parties = [p.strip() for p in reponse_propre.split("|")]

    def get(i, defaut=""):
        return parties[i] if len(parties) > i else defaut

    visibilite = get(0, "ok")
    genre = get(1, "neutre").lower()
    if genre not in ("masculin", "feminin", "neutre"):
        genre = "neutre"

    n = len(parties)

    if n >= 9:
        # Mode Dilemme
        result = {
            "mode": "dilemme",
            "visibilite": visibilite,
            "genre": genre,
            "desc_a": get(2),
            "desc_b": get(3),
            "gagnante": get(4, "A"),
            "score_a": get(5, "?/10"),
            "score_b": get(6, "?/10"),
            "analyse": get(7),
            "accessoire": get(8, ""),
        }
    elif n >= 8:
        # Analyse classique Drip
        acc = get(7, "")
        if acc.lower() in ("none", "aucun", ""):
            acc = ""
        result = {
            "mode": "drip",
            "visibilite": visibilite,
            "genre": genre,
            "description": get(2),
            "score": get(3, "?/10"),
            "titre": get(4, "Analyse"),
            "analyse": get(5, reponse_propre),
            "conseil": get(6),
            "accessoire": acc,
        }
    else:
        # Roast (7 champs) ou réponse courte (erreur visibilité)
        result = {
            "mode": "roast",
            "visibilite": visibilite,
            "genre": genre,
            "description": get(2),
            "score": get(3, "?/10"),
            "titre": get(4, "Analyse"),
            "analyse": get(5, reponse_propre),
            "conseil": get(6),
            "accessoire": "",
        }

    # Normalisation accessoire
    acc = result.get("accessoire", "")
    if acc.lower() in ("none", "aucun", ""):
        result["accessoire"] = ""

    return result


def construire_prompt(mode: str, situation_desc: str, intention: str) -> str:
    """Injecte contexte + intention dans le bon template."""
    intention_block = (
        f"\nINTENTION DE STYLE DE L'UTILISATEUR : « {intention} »\n"
        "Évalue si la tenue correspond à cette intention — c'est un critère clé de l'analyse.\n"
        if intention.strip() else ""
    )
    if mode == "drip":
        return PROMPT_DRIP_TEMPLATE.format(
            situation=situation_desc,
            intention_block=intention_block,
            catalog_lines=_CATALOG_LINES,
            catalog_keys=_CATALOG_KEYS,
        )
    elif mode == "dilemme":
        return PROMPT_DILEMME_TEMPLATE.format(
            situation=situation_desc,
            intention_block=intention_block,
            catalog_lines=_CATALOG_LINES,
            catalog_keys=_CATALOG_KEYS,
        )
    else:
        return PROMPT_ROAST_TEMPLATE.format(
            situation=situation_desc,
            intention_block=intention_block,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 3b — RATE LIMITING (3 analyses gratuites / jour)
# ══════════════════════════════════════════════════════════════════════════════

def init_rate_limit():
    """Initialise les clés de suivi dans st.session_state si elles n'existent pas."""
    today_str = date.today().isoformat()
    if "last_analysis_date" not in st.session_state:
        st.session_state.last_analysis_date = today_str
        st.session_state.analyses_today = 0
    # Remise à zéro si nouveau jour
    elif st.session_state.last_analysis_date != today_str:
        st.session_state.last_analysis_date = today_str
        st.session_state.analyses_today = 0


def peut_analyser() -> bool:
    """Retourne True si l'utilisateur n'a pas encore atteint sa limite du jour."""
    return st.session_state.analyses_today < MAX_ANALYSES_PAR_JOUR


def incrementer_compteur():
    """Incrémente le compteur d'analyses du jour."""
    st.session_state.analyses_today += 1


def analyses_restantes() -> int:
    """Retourne le nombre d'analyses gratuites restantes pour aujourd'hui."""
    return max(0, MAX_ANALYSES_PAR_JOUR - st.session_state.analyses_today)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 3c — GÉNÉRATION STORY (Pillow 9:16 Instagram/TikTok)
# ══════════════════════════════════════════════════════════════════════════════
def generer_phrase_story(analyse: str) -> str:
    """
    Demande à l'IA de condenser l'analyse en une phrase unique,
    punchy et pensée pour les réseaux sociaux.
    Fallback : résume manuellement sur la 1ère phrase nettoyée.
    """
    if not analyse or not analyse.strip():
        return "Mon style, ma signature. ✦"
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=80,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un copywriter mode ultra-concis. "
                        "Résume l'analyse de style donnée en UNE SEULE phrase "
                        "percutante (max 12 mots), sans hashtag, sans guillemets, "
                        "sans ponctuation finale. Écris uniquement la phrase, rien d'autre."
                    ),
                },
                {"role": "user", "content": analyse},
            ],
        )
        phrase = resp.choices[0].message.content.strip().strip('"').strip("'")
        # Sécurité : si l'IA hallucine plus de 100 caractères, on tronque proprement
        if len(phrase) > 100:
            phrase = phrase[:97].rstrip() + "…"
        return phrase
    except Exception:
        # Fallback silencieux : 1ère phrase de l'analyse
        premiere = re.split(r'(?<=[.!?])\s', analyse.strip())[0]
        return premiere[:90].rstrip() + ("…" if len(premiere) > 90 else "")

def charger_police(taille: int):
    """
    Charge une police système avec fallback robuste.
    Essaie plusieurs chemins communs avant de tomber sur la police par défaut PIL.
    """
    polices_candidates = [
        # Linux / Streamlit Cloud
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        # macOS
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFProDisplay-Bold.otf",
        # Windows
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for chemin in polices_candidates:
        try:
            return ImageFont.truetype(chemin, taille)
        except (IOError, OSError):
            continue
    # Fallback : police bitmap par défaut (toujours disponible)
    return ImageFont.load_default()


def charger_police_light(taille: int):
    """Version light/regular de la police pour les corps de texte."""
    polices_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for chemin in polices_candidates:
        try:
            return ImageFont.truetype(chemin, taille)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def generer_story(image_pil: Image.Image, score: str, titre: str, analyse: str) -> bytes:
    """
    Génère une image Story 9:16 (1080×1920 px) — design premium refonte :
      - Photo pleine largeur sur 65 % de la hauteur avec dégradé profond
      - Pastille score dorée centrée à cheval sur la photo et la zone texte
      - Phrase-résumé IA ultra-courte (1 phrase, générée par GPT)
      - Titre du style en petites capitales élégantes
      - Footer branding centré, typographie fine
    """
    LARGEUR, HAUTEUR   = 1080, 1920
    ZONE_IMAGE_H       = int(HAUTEUR * 0.62)   # 62 % pour la photo (plus immersif)
    COULEUR_FOND       = (14, 13, 11)           # Noir profond quasi-absolu
    COULEUR_ACCENT     = (185, 148, 95)         # Or chaud premium
    COULEUR_ACCENT2    = (210, 175, 120)        # Or clair pour highlights
    COULEUR_TEXTE      = (240, 238, 232)        # Blanc cassé doux
    COULEUR_MUTED      = (120, 116, 108)        # Gris chaud discret
    COULEUR_DIVIDER    = (45, 43, 38)           # Séparateur très subtil

    # ── Canvas ───────────────────────────────────────────────────────────────
    story = Image.new("RGB", (LARGEUR, HAUTEUR), COULEUR_FOND)
    draw  = ImageDraw.Draw(story)

    # ── Photo utilisateur ────────────────────────────────────────────────────
    img = image_pil.copy().convert("RGB")
    ratio_cible = LARGEUR / ZONE_IMAGE_H
    w, h = img.size
    ratio_actuel = w / h

    if ratio_actuel > ratio_cible:
        new_w = int(h * ratio_cible)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / ratio_cible)
        img = img.crop((0, 0, w, new_h))

    img = img.resize((LARGEUR, ZONE_IMAGE_H), Image.LANCZOS)

    # Dégradé bas : fondu exponentiel sur 42 % du bas → noir total
    fondu = Image.new("L", (LARGEUR, ZONE_IMAGE_H), 255)
    px_fondu = fondu.load()
    zone_fondu = int(ZONE_IMAGE_H * 0.42)
    debut_fondu = ZONE_IMAGE_H - zone_fondu
    for y in range(debut_fondu, ZONE_IMAGE_H):
        t = (y - debut_fondu) / zone_fondu
        alpha = int(255 * (1 - t ** 1.6))
        for x in range(LARGEUR):
            px_fondu[x, y] = alpha

    # Vignette latérale : masque qui assombrit les bords gauche/droite
    vignette = Image.new("L", (LARGEUR, ZONE_IMAGE_H), 255)
    pv = vignette.load()
    for x in range(LARGEUR):
        t_left = max(0.0, 1.0 - x / (LARGEUR * 0.18))
        t_right = max(0.0, 1.0 - (LARGEUR - 1 - x) / (LARGEUR * 0.18))
        attenuation = max(t_left, t_right) * 0.55  # 0 au centre, 0.55 aux bords
        for y in range(ZONE_IMAGE_H):
            pv[x, y] = int(255 * (1.0 - attenuation))  # 255 = garde photo, < 255 = assombrit

    # Combiner : d'abord fondu bas, ensuite vignette latérale — tout sur la photo directement
    fond_noir = Image.new("RGB", (LARGEUR, ZONE_IMAGE_H), COULEUR_FOND)

    # Étape 1 : appliquer le fondu bas (photo → noir en bas)
    img_step1 = Image.composite(img, fond_noir, fondu)

    # Étape 2 : appliquer la vignette latérale (assombrit les côtés)
    img_final = Image.composite(img_step1, fond_noir, vignette)

    story.paste(img_final, (0, 0))

    # ── Pastille score dorée — centrée horizontalement ────────────────────────
    PASTILLE_R  = 130                                # rayon
    cx          = LARGEUR // 2                       # centre horizontal
    cy          = ZONE_IMAGE_H - 20                  # à cheval sur la photo
    bbox_pastille = [cx - PASTILLE_R, cy - PASTILLE_R, cx + PASTILLE_R, cy + PASTILLE_R]

    # Halo très doux derrière la pastille
    for offset in range(22, 0, -4):
        alpha_halo = int(30 * (offset / 22))
        draw.ellipse(
            [cx - PASTILLE_R - offset, cy - PASTILLE_R - offset,
             cx + PASTILLE_R + offset, cy + PASTILLE_R + offset],
            fill=(185, 148, 95, alpha_halo),
        )
    # Disque doré
    draw.ellipse(bbox_pastille, fill=COULEUR_ACCENT)

    # Anneau intérieur fin
    draw.ellipse(
        [cx - PASTILLE_R + 8, cy - PASTILLE_R + 8,
         cx + PASTILLE_R - 8, cy + PASTILLE_R - 8],
        outline=(210, 175, 120),
        width=2,
    )

    # Chiffre du score
    score_propre = score.replace("/10", "").strip()
    font_score_pastille = charger_police(108)
    try:
        bbox_s = font_score_pastille.getbbox(score_propre)
        sw = bbox_s[2] - bbox_s[0]
        sh = bbox_s[3] - bbox_s[1]
        sy = bbox_s[1]  # offset vertical réel de la police
    except Exception:
        sw, sh, sy = 80, 100, 0
    draw.text(
        (cx - sw // 2, cy - PASTILLE_R // 2 - sh // 2),
        score_propre,
        fill=COULEUR_FOND,
        font=font_score_pastille,
    )

    # "/10" — ancré juste sous le chiffre, centré
    font_sub = charger_police(34)
    try:
        bbox_sub = font_sub.getbbox("/10")
        sub_w = bbox_sub[2] - bbox_sub[0]
    except Exception:
        sub_w = 44
    draw.text(
        (cx - sub_w // 2, cy - PASTILLE_R // 2 + sh + 6),
        "/10",
        fill=(40, 38, 34),
        font=font_sub,
    )

    # ── Zone texte ────────────────────────────────────────────────────────────
    padding_x  = 90
    y_curseur  = cy + PASTILLE_R + 58          # démarre sous la pastille

    # Ligne décorative gauche
    draw.rectangle(
        [(padding_x, y_curseur), (padding_x + 48, y_curseur + 2)],
        fill=COULEUR_ACCENT,
    )
    # Ligne décorative droite (symétrique)
    draw.rectangle(
        [(LARGEUR - padding_x - 48, y_curseur), (LARGEUR - padding_x, y_curseur + 2)],
        fill=COULEUR_ACCENT,
    )
    y_curseur += 40

    # Titre du style — centré, petites capitales simulées
    font_titre = charger_police(52)
    titre_affiche = titre[:38].upper() + ("…" if len(titre) > 38 else "")
    try:
        bbox_t   = font_titre.getbbox(titre_affiche)
        titre_w  = bbox_t[2] - bbox_t[0]
    except Exception:
        titre_w  = 600
    draw.text(
        ((LARGEUR - titre_w) // 2, y_curseur),
        titre_affiche,
        fill=COULEUR_TEXTE,
        font=font_titre,
    )
    y_curseur += 76

    # Séparateur très fin centré
    sep_w = 200
    draw.rectangle(
        [(LARGEUR // 2 - sep_w // 2, y_curseur),
         (LARGEUR // 2 + sep_w // 2, y_curseur + 1)],
        fill=COULEUR_DIVIDER,
    )
    y_curseur += 38

    # ── Phrase-résumé IA (générée, 1 phrase entière et punchy) ───────────────
    phrase_story = generer_phrase_story(analyse)

    font_phrase = charger_police_light(42)
    largeur_utile = LARGEUR - (padding_x * 2)
    try:
        largeur_x = font_phrase.getlength("x")
    except AttributeError:
        largeur_x = 23
    chars_par_ligne = max(24, int(largeur_utile / largeur_x))

    lignes = textwrap.wrap(phrase_story, width=chars_par_ligne)
    lignes = lignes[:3]          # max 3 lignes — garanti propre visuellement

    ligne_h = 60
    for ligne in lignes:
        try:
            bbox_l  = font_phrase.getbbox(ligne)
            ligne_w = bbox_l[2] - bbox_l[0]
        except Exception:
            ligne_w = largeur_utile
        # Centrage horizontal de chaque ligne
        x_ligne = (LARGEUR - ligne_w) // 2
        draw.text((x_ligne, y_curseur), ligne, fill=COULEUR_TEXTE, font=font_phrase)
        y_curseur += ligne_h

    # ── Footer branding ───────────────────────────────────────────────────────
    footer_y      = HAUTEUR - 90
    # Trait de séparation footer
    draw.rectangle(
        [(LARGEUR // 2 - 120, footer_y - 22), (LARGEUR // 2 + 120, footer_y - 21)],
        fill=COULEUR_DIVIDER,
    )
    font_footer   = charger_police(30)
    footer_txt    = "✦  JUGE MON STYLE  ✦"
    try:
        bbox_f    = font_footer.getbbox(footer_txt)
        footer_w  = bbox_f[2] - bbox_f[0]
    except Exception:
        footer_w  = 260
    draw.text(
        ((LARGEUR - footer_w) // 2, footer_y),
        footer_txt,
        fill=COULEUR_MUTED,
        font=font_footer,
    )

    # ── Export JPEG ───────────────────────────────────────────────────────────
    buffer = io.BytesIO()
    story.save(buffer, format="JPEG", quality=92, optimize=True)
    buffer.seek(0)
    return buffer.read()


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — PROMPTS IA (analyses enrichies : 5-6 phrases dans "Analyse experte")
# ══════════════════════════════════════════════════════════════════════════════

PROMPT_DRIP_TEMPLATE = """\
Tu es un(e) styliste personnel(le) expert(e) — bienveillant(e), direct(e) et pédagogique. \
Tu analyses les tenues avec l'œil d'un(e) professionnel(le) qui veut vraiment aider. \
Tu expliques le POURQUOI de chaque conseil avec de vraies règles de style \
(colorimétrie, morphologie, équilibre des volumes, règle du 3e pièce, contraste tonal, etc.).

━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTE : Cette tenue est portée pour {situation}.
{intention_block}\
━━━━━━━━━━━━━━━━━━━━━━━━━━

CATALOGUE D'ACCESSOIRES (pour la recommandation finale) :
{catalog_lines}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROCESSUS D'ANALYSE — réfléchis dans une balise <reflexion> avant le verdict.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ÉTAPE 1 — ÉVALUATION DE LA PHOTO :
Règle d'or : tu analyses TOUJOURS la tenue avec ce que tu vois, même si la photo est imparfaite.
→ Ne renvoie "erreur" QUE si l'image est entièrement hors-sujet (pas de personne), \
entièrement noire/illisible, ou si aucun vêtement n'est visible du tout.
→ Dans tous les autres cas : note "ok" et intègre un avertissement bienveillant \
d'une phrase dans le champ "description" si pertinent.

ÉTAPE 2 — GENRE DE PRÉSENTATION :
"masculin", "feminin" ou "neutre" selon les codes vestimentaires visibles.

ÉTAPE 3 — INVENTAIRE PRÉCIS :
Chaque pièce visible : type exact, couleur précise ("bleu ardoise" pas "bleu"), \
matière apparente, coupe.

ÉTAPE 4 — ANALYSE EXPERTE APPROFONDIE :
  · COLORIMÉTRIE : harmonie analogique/complémentaire ? Contraste tonal ? Rappels de couleur ?
  · MORPHOLOGIE : volumes équilibrés (règle haut volumineux → bas ajusté) ?
  · RÈGLE DU 3e PIÈCE : y a-t-il un élément qui élève la tenue ?
  · ADÉQUATION CONTEXTE & INTENTION : la tenue remplit-elle son rôle ?
  · POINTS FORTS & POINTS FAIBLES : que fonctionne exactement, et que pourrait-on améliorer ?

ÉTAPE 5 — ACCESSOIRE CATALOGUE : lequel apporte la valeur ajoutée la plus immédiate ?

ÉTAPE 6 — VERDICT : note sur 10, nom de style (3-4 mots), conseil principal.

<reflexion> reste privée — elle N'APPARAÎT PAS dans la réponse publique.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT DE RÉPONSE PUBLIQUE (après </reflexion>) :
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Si vraie erreur (image entièrement illisible/hors-sujet) → 3 champs :
erreur:[raison courte] | neutre | [Message doux expliquant comment retenter — 1 phrase]

Sinon (= quasi toujours) → exactement 8 champs séparés par | :
ok | [masculin/feminin/neutre] | [Description 3-4 phrases : chaque pièce visible, \
couleur exacte, matière, coupe. Inclure ici tout avertissement photo si besoin.] | \
[Note]/10 | [Nom du style 3-4 mots] | \
[Analyse experte DÉTAILLÉE — IMPÉRATIF : environ 4 phrases riches qui s'appuient sur \
ton raisonnement dans <reflexion>. Explique PRÉCISÉMENT pourquoi la coupe fonctionne \
ou non (morphologie, équilibre des volumes), pourquoi les couleurs s'accordent \
(colorimétrie, contraste tonal, rappels de couleur), nomme la règle de style appliquée \
(règle du 3e pièce, 60-30-10, etc.), évalue l'adéquation avec le contexte et l'intention, \
et conclus avec le point le plus fort de la tenue. Pronoms adaptés au genre.] | \
[Conseil concret — explique le POURQUOI avec une règle précise] | \
[ID accessoire parmi {catalog_keys} ou "none"]

RÈGLES ABSOLUES :
- Champ 8 : uniquement parmi {catalog_keys} ou "none". Jamais d'ID inventé.
- Ton : chaleureux, expert, jamais condescendant.
- L'analyse (champ 6) doit faire environ 4 phrases. C'est le cœur de la valeur ajoutée.
- Ne rien écrire hors format après </reflexion>.
"""

PROMPT_DILEMME_TEMPLATE = """\
Tu es un(e) styliste personnel(le) expert(e). \
L'utilisateur te soumet DEUX tenues (image A et image B) et veut savoir laquelle choisir. \
Tu joues le rôle d'un(e) ami(e) honnête dans la cabine d'essayage : \
bienveillant(e), précis(e), et tu justifies chaque choix avec une règle de style réelle.

━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTE : Ces tenues sont portées pour {situation}.
{intention_block}\
━━━━━━━━━━━━━━━━━━━━━━━━━━

CATALOGUE D'ACCESSOIRES :
{catalog_lines}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROCESSUS D'ANALYSE — réfléchis dans une balise <reflexion>.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ÉTAPE 1 — ÉVALUATION DES PHOTOS (même règle : analyse ce que tu vois).
ÉTAPE 2 — GENRE de présentation global (pour adapter les pronoms).
ÉTAPE 3 — ANALYSE TENUE A : inventaire, colorimétrie, morphologie, adéquation contexte.
ÉTAPE 4 — ANALYSE TENUE B : idem.
ÉTAPE 5 — COMPARAISON : avantages relatifs de chaque tenue pour ce contexte et cette intention.
ÉTAPE 6 — VERDICT : laquelle gagne et pourquoi (règle de style décisive) ?

<reflexion> reste privée.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT DE RÉPONSE PUBLIQUE (après </reflexion>) :
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Si vraie erreur → 3 champs :
erreur:[raison] | neutre | [Explication douce — comment retenter]

Sinon → exactement 9 champs séparés par | :
ok | [masculin/feminin/neutre] | [Description tenue A — pièces, couleurs, matières] | \
[Description tenue B — pièces, couleurs, matières] | [A ou B — la gagnante] | \
[Score tenue A]/10 | [Score tenue B]/10 | \
[Analyse comparative DÉTAILLÉE — IMPÉRATIF : environ 5 phrases riches qui s'appuient sur \
ton raisonnement dans <reflexion>. Explique les points forts de chaque tenue, \
nomme la règle de style décisive (ex: contraste tonal, adéquation morphologique, \
règle du 3e pièce), justifie précisément pourquoi la gagnante l'emporte pour CE contexte, \
donne un conseil d'amélioration concret pour la perdante, et évalue l'adéquation \
contexte + intention. Pronoms adaptés.] | \
[ID accessoire parmi {catalog_keys} ou "none"]

RÈGLES ABSOLUES :
- Champ 9 : uniquement parmi {catalog_keys} ou "none".
- L'analyse comparative (champ 8) doit faire 5 phrases environ.
- Ne rien écrire hors format après </reflexion>.
"""

PROMPT_ROAST_TEMPLATE = """\
Tu es un(e) critique vestimentaire légendairement sans pitié. \
Ton humour est chirurgical, tes comparaisons sont absurdes et mémorables. \
Tu es impitoyable comme Gordon Ramsay dans une friperie, \
avec le vocabulaire d'un(e) rédacteur(trice) de mode qui aurait grandi sur Twitter.

━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTE : Cette tenue est portée pour {situation}.
{intention_block}\
━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROCESSUS — réfléchis dans une balise <reflexion>.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ÉTAPE 1 — ÉVALUATION DE LA PHOTO :
Tu analyses toujours avec ce que tu vois. \
Ne renvoie "erreur" que si l'image est entièrement noire/illisible. \
Si la photo est imparfaite, intègre-le dans le roast avec humour.

ÉTAPE 2 — GENRE de présentation (pronoms à adapter).
ÉTAPE 3 — INVENTAIRE DES CRIMES : chaque pièce visible et son problème principal.
ÉTAPE 4 — HIÉRARCHIE : LE pire élément — cœur du roast.
ÉTAPE 5 — ANGLE CONTEXTUEL : comment "{situation}" amplifie le désastre ?
ÉTAPE 6 — PUNCHLINES : 3 comparaisons ridicules → retenir la plus dévastatrice + sentence finale.

<reflexion> reste privée.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT DE RÉPONSE PUBLIQUE (après </reflexion>) :
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Si vraie erreur (image entièrement illisible) → 3 champs :
erreur:[raison] | neutre | [Le critique est agacé — dit clairement pourquoi c'est inutilisable]

Sinon → exactement 7 champs séparés par | :
ok | [masculin/feminin/neutre] | [Description 2-3 phrases — précise, déjà légèrement sarcastique] | \
[Note]/10 | [Titre humiliant 3-4 mots] | \
[Roast — 2-3 phrases percutantes, contexte exploité, pronoms adaptés] | \
[Sentence finale — punchline courte et mortelle]

RÈGLES ABSOLUES :
- Humour, jamais de haine réelle. Attaque uniquement les vêtements, pas le physique.
- Ne rien écrire hors format après </reflexion>.
"""


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — SESSION STATE & QUERY PARAMS
# ══════════════════════════════════════════════════════════════════════════════

if "a_paye" not in st.session_state:
    st.session_state.a_paye = False
if "saved_image" not in st.session_state:
    st.session_state.saved_image = None          # bytes de l'image sauvegardée
if "auto_roast" not in st.session_state:
    st.session_state.auto_roast = False          # déclencher l'analyse auto au retour

# Initialisation du rate limiter
init_rate_limit()

payment_param = st.query_params.get("payment", "")
if payment_param == "success" and not st.session_state.a_paye:
    st.session_state.a_paye = True
    st.session_state.auto_roast = True           # déclenche le roast automatique
    st.query_params.clear()
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 6 — CSS PREMIUM (light mode épuré, typographie clean)
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&family=Inter:wght@300;400;500;600&display=swap');

/* ── Palette & variables ─────────────────────────────────────────── */
:root {
    --bg:          #FAFAF8;
    --surface:     #FFFFFF;
    --surface-2:   #F5F4F0;
    --border:      #E8E6E0;
    --border-soft: #F0EEE8;
    --text-primary:   #1A1A18;
    --text-secondary: #6B6960;
    --text-muted:     #A8A49C;
    --accent:      #2C2C28;
    --accent-warm: #8B6F47;
    --accent-soft: #F2EDE5;
    --success-bg:  #F0F7F0;
    --success-border: #C8DEC8;
    --success-text:   #2A5A2A;
    --warning-bg:  #FDF6EC;
    --warning-border: #E8D4A8;
    --warning-text:   #7A5A20;
    --danger-bg:   #FDF0F0;
    --danger-border:  #E8C8C8;
    --danger-text:    #6A2020;
    --radius-sm: 8px;
    --radius-md: 14px;
    --radius-lg: 20px;
    --radius-xl: 28px;
    --shadow-sm: 0 1px 4px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 16px rgba(0,0,0,0.08);
    --shadow-lg: 0 8px 32px rgba(0,0,0,0.10);
}

/* ── Reset & base ────────────────────────────────────────────────── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background-color: var(--bg) !important;
    color: var(--text-primary);
    font-family: 'Inter', sans-serif;
    font-weight: 400;
}

#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="collapsedControl"] { display: none !important; }

[data-testid="stMain"] > div:first-child { padding-top: 2.5rem !important; }
.block-container {
    max-width: 560px !important;
    padding: 0 1.4rem 5rem !important;
    margin: 0 auto;
}

/* ── Header ──────────────────────────────────────────────────────── */
.app-header {
    text-align: center;
    padding: 2rem 1rem 1.5rem;
}
.app-eyebrow {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 3px;
    color: var(--text-muted);
    font-weight: 500;
    margin-bottom: 0.8rem;
}
.app-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: clamp(2rem, 8vw, 3rem);
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.15;
    letter-spacing: -0.5px;
    margin: 0 0 0.6rem;
}
.app-title em {
    font-style: italic;
    color: var(--accent-warm);
}
.app-subtitle {
    font-size: 0.95rem;
    color: var(--text-secondary);
    font-weight: 300;
    line-height: 1.6;
    max-width: 380px;
    margin: 0 auto;
}
.header-divider {
    height: 1px;
    background: var(--border);
    border: none;
    margin: 1.8rem 0;
}

/* ── Section labels ──────────────────────────────────────────────── */
.section-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--text-muted);
    font-weight: 600;
    display: block;
    margin: 1.8rem 0 0.8rem;
}

/* ── Upload zones ────────────────────────────────────────────────── */
[data-testid="stFileUploader"] {
    background: var(--surface) !important;
    border: 1.5px dashed var(--border) !important;
    border-radius: var(--radius-lg) !important;
    padding: 0.8rem !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--accent-warm) !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stFileUploader"] label {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
    color: var(--text-secondary) !important;
    font-weight: 400 !important;
}
[data-testid="stFileUploaderDropzone"] {
    background: transparent !important;
    border: none !important;
}

/* ── Images uploadées ────────────────────────────────────────────── */
[data-testid="stImage"] img {
    border-radius: var(--radius-md) !important;
    object-fit: cover;
    width: 100%;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stImage"] > div > p {
    font-size: 0.72rem !important;
    color: var(--text-muted) !important;
    text-align: center;
    margin-top: 0.4rem;
}

/* ── Mode selector (radio) ───────────────────────────────────────── */
.mode-cards { display: flex; gap: 0.8rem; margin: 0.8rem 0; }
[data-testid="stRadio"] > div {
    gap: 0.6rem !important;
    flex-direction: column !important;
}
[data-testid="stRadio"] label {
    background: var(--surface) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    padding: 0.85rem 1rem !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    color: var(--text-secondary) !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
    width: 100% !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stRadio"] label:hover {
    border-color: var(--accent-warm) !important;
    color: var(--text-primary) !important;
    background: var(--accent-soft) !important;
}
[data-testid="stRadio"] label:has(input:checked) {
    border-color: var(--accent) !important;
    background: var(--accent-soft) !important;
    color: var(--text-primary) !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stRadio"] input[type="radio"] { display: none !important; }

/* ── Pills (situation) ───────────────────────────────────────────── */
[data-testid="stPills"] { gap: 0.4rem !important; flex-wrap: wrap !important; }
[data-testid="stPills"] button {
    background: var(--surface) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 50px !important;
    color: var(--text-secondary) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.35rem 0.85rem !important;
    transition: all 0.18s ease !important;
}
[data-testid="stPills"] button:hover {
    border-color: var(--accent-warm) !important;
    color: var(--text-primary) !important;
    background: var(--accent-soft) !important;
}
[data-testid="stPills"] button[aria-selected="true"],
[data-testid="stPills"] button[data-selected="true"] {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    color: #FFFFFF !important;
}

/* ── Selectbox fallback ──────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background: var(--surface) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
}
[data-testid="stSelectbox"] > div > div:hover {
    border-color: var(--accent-warm) !important;
}

/* ── Text input (intention) ──────────────────────────────────────── */
[data-testid="stTextInput"] input {
    background: var(--surface) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
    padding: 0.7rem 1rem !important;
    transition: border-color 0.2s ease !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--accent-warm) !important;
    box-shadow: 0 0 0 3px rgba(139, 111, 71, 0.12) !important;
}
[data-testid="stTextInput"] input::placeholder { color: var(--text-muted) !important; }
[data-testid="stTextInput"] label {
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 2px !important;
    color: var(--text-muted) !important;
    font-weight: 600 !important;
}

/* ── Bouton principal ────────────────────────────────────────────── */
div.stButton > button:first-child {
    background-color: var(--accent) !important;
    background-image: none !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 50px !important;
    padding: 0.9rem 2.2rem !important;
    font-size: 0.9rem !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    width: 100% !important;
    margin-top: 0.6rem !important;
    transition: background-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease !important;
    box-shadow: 0 2px 12px rgba(44, 44, 40, 0.18) !important;
    cursor: pointer !important;
    -webkit-text-fill-color: #FFFFFF !important;
}
div.stButton > button:first-child * {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}
div.stButton > button:first-child:hover {
    background-color: #3D3D38 !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(44, 44, 40, 0.22) !important;
}
div.stButton > button:first-child:active,
div.stButton > button:first-child:focus {
    background-color: #1E1E1B !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    transform: translateY(0) !important;
    box-shadow: 0 1px 6px rgba(44, 44, 40, 0.15) !important;
    outline: none !important;
}

/* ── Download button (Story) ─────────────────────────────────────── */
div.stDownloadButton > button {
    background-color: var(--accent-warm) !important;
    background-image: none !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 50px !important;
    padding: 0.75rem 2rem !important;
    font-size: 0.88rem !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    width: 100% !important;
    margin-top: 0.4rem !important;
    -webkit-text-fill-color: #FFFFFF !important;
    box-shadow: 0 2px 10px rgba(139, 111, 71, 0.25) !important;
    transition: background-color 0.2s ease, transform 0.2s ease !important;
}
div.stDownloadButton > button:hover {
    background-color: #7A5E38 !important;
    transform: translateY(-1px) !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

/* ── Spinner ─────────────────────────────────────────────────────── */
[data-testid="stSpinner"] p {
    color: var(--text-secondary) !important;
    font-size: 0.88rem !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Alertes Streamlit (success / error) ─────────────────────────── */
[data-testid="stAlert"] {
    border-radius: var(--radius-md) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.92rem !important;
    line-height: 1.65 !important;
    padding: 1.1rem 1.3rem !important;
    border-left-width: 3px !important;
}

/* ── Card résultat — wrapper ─────────────────────────────────────── */
.result-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-xl);
    padding: 1.4rem;
    margin-top: 1.2rem;
    box-shadow: var(--shadow-sm);
}

/* ── Badge contexte ──────────────────────────────────────────────── */
.context-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 50px;
    padding: 0.3rem 0.85rem;
    font-size: 0.75rem;
    color: var(--text-secondary);
    font-weight: 500;
    margin-bottom: 1.2rem;
}

/* ── Card description "Ce que je vois" ──────────────────────────── */
.desc-card {
    background: var(--surface-2);
    border: 1px solid var(--border-soft);
    border-left: 3px solid var(--accent-warm);
    border-radius: var(--radius-md);
    padding: 1rem 1.2rem;
    margin: 1rem 0 0.8rem;
}
.desc-card-header {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--accent-warm);
    font-weight: 600;
    margin-bottom: 0.55rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.desc-card-header::after {
    content: "";
    flex: 1;
    height: 1px;
    background: var(--border);
}
.desc-card-body {
    font-size: 0.88rem;
    color: var(--text-secondary);
    line-height: 1.7;
    font-style: italic;
}
.genre-badge {
    display: inline-block;
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 600;
    font-style: normal;
    padding: 0.12rem 0.5rem;
    border-radius: 50px;
    margin-left: 0.4rem;
    vertical-align: middle;
}
.genre-masculin  { background: #EEF4FF; color: #3B6FCC; border: 1px solid #C8D8F4; }
.genre-feminin   { background: #FFF0F5; color: #CC3B6F; border: 1px solid #F4C8D8; }
.genre-neutre    { background: var(--surface-2); color: var(--text-muted); border: 1px solid var(--border); }

/* ── Score ───────────────────────────────────────────────────────── */
.score-block {
    text-align: center;
    padding: 1.2rem 0 0.8rem;
}
.score-number {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 3.6rem;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1;
    letter-spacing: -1px;
}
.score-label {
    font-size: 0.65rem;
    color: var(--text-muted);
    letter-spacing: 2.5px;
    text-transform: uppercase;
    font-weight: 500;
    margin-top: 0.2rem;
}
.score-accent {
    color: var(--accent-warm);
}

/* ── Mode Dilemme : comparaison A/B ─────────────────────────────── */
.dilemme-scores {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.8rem;
    margin: 1rem 0;
}
.dilemme-score-cell {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 0.9rem;
    text-align: center;
}
.dilemme-score-cell.winner {
    background: var(--success-bg);
    border-color: var(--success-border);
}
.dilemme-score-label {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--text-muted);
    font-weight: 600;
    margin-bottom: 0.3rem;
}
.dilemme-score-value {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 2.2rem;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1;
}
.dilemme-score-cell.winner .dilemme-score-value { color: var(--success-text); }
.winner-badge {
    display: inline-block;
    background: var(--success-bg);
    color: var(--success-text);
    border: 1px solid var(--success-border);
    border-radius: 50px;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.2rem 0.7rem;
    margin-top: 0.4rem;
    letter-spacing: 0.5px;
}

/* ── Erreur visibilité ───────────────────────────────────────────── */
.visibility-error {
    background: var(--warning-bg);
    border: 1px solid var(--warning-border);
    border-radius: var(--radius-lg);
    padding: 1.4rem 1.6rem;
    text-align: center;
    margin-top: 1rem;
}
.ve-icon { font-size: 1.8rem; margin-bottom: 0.5rem; }
.ve-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--warning-text);
    margin-bottom: 0.5rem;
}
.ve-body {
    font-size: 0.88rem;
    color: var(--warning-text);
    line-height: 1.65;
    opacity: 0.85;
}

/* ── Card affiliation ────────────────────────────────────────────── */
.affil-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1rem 1.2rem;
    margin-top: 1rem;
    text-decoration: none !important;
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
}
.affil-card::before {
    content: "";
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: var(--accent-warm);
    border-radius: 0 2px 2px 0;
}
.affil-card:hover {
    box-shadow: var(--shadow-md);
    transform: translateY(-1px);
    border-color: var(--accent-warm);
}
.affil-emoji {
    font-size: 1.6rem;
    flex-shrink: 0;
    width: 2.5rem;
    text-align: center;
    color: var(--accent-warm);
    font-family: 'Playfair Display', serif;
    font-size: 1.2rem;
    font-weight: 600;
}
.affil-body { flex: 1; min-width: 0; }
.affil-header {
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--accent-warm);
    font-weight: 600;
    margin-bottom: 0.15rem;
}
.affil-name {
    font-family: 'Playfair Display', serif;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.2;
}
.affil-tagline {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 0.1rem;
}
.affil-cta {
    flex-shrink: 0;
    background-color: var(--accent);
    background-image: none;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    text-decoration: none !important;
    border-radius: 50px;
    padding: 0.4rem 1rem;
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    font-weight: 600;
    white-space: nowrap;
    transition: background-color 0.2s ease;
    display: inline-block;
}
.affil-cta:hover {
    background-color: #3D3D38;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    text-decoration: none !important;
}

/* ── Stripe payment button ───────────────────────────────────────── */
.stripe-btn-wrapper { margin-top: 0.6rem; }
.stripe-btn {
    display: block;
    width: 100%;
    padding: 0.9rem 2rem;
    background-color: var(--accent);
    background-image: none;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    text-decoration: none !important;
    border-radius: 50px;
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    font-weight: 600;
    text-align: center;
    box-shadow: 0 2px 12px rgba(44, 44, 40, 0.18);
    transition: background-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
    box-sizing: border-box;
}
.stripe-btn:hover {
    background-color: #3D3D38;
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(44, 44, 40, 0.22);
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    text-decoration: none !important;
}
.stripe-btn:active {
    background-color: #1E1E1B;
    transform: translateY(0);
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}
.stripe-sub {
    text-align: center;
    font-size: 0.72rem;
    color: var(--text-muted);
    margin-top: 0.6rem;
    letter-spacing: 0.2px;
}

/* ── Bannière paiement validé ────────────────────────────────────── */
.payment-success-banner {
    background: var(--success-bg);
    border: 1px solid var(--success-border);
    border-radius: var(--radius-lg);
    padding: 1.2rem 1.4rem;
    text-align: center;
    margin-bottom: 1.4rem;
}
.payment-success-banner .check { font-size: 1.6rem; margin-bottom: 0.3rem; }
.payment-success-banner h3 {
    font-family: 'Playfair Display', serif;
    font-size: 1rem;
    font-weight: 600;
    color: var(--success-text);
    margin: 0 0 0.3rem;
}
.payment-success-banner p {
    font-size: 0.85rem;
    color: var(--success-text);
    opacity: 0.75;
    margin: 0;
}

/* ── Expander CoT ────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: var(--surface-2) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: var(--radius-md) !important;
    margin-top: 0.8rem !important;
}
[data-testid="stExpander"] summary {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.8rem !important;
    color: var(--text-secondary) !important;
    padding: 0.7rem 1rem !important;
    letter-spacing: 0.2px !important;
}
[data-testid="stExpander"] summary:hover { color: var(--text-primary) !important; }
[data-testid="stExpander"] > div > div {
    padding: 0 1rem 0.8rem !important;
    font-size: 0.8rem !important;
    color: var(--text-muted) !important;
    line-height: 1.65 !important;
    font-style: italic;
    white-space: pre-wrap;
}

/* ── Footer ──────────────────────────────────────────────────────── */
.custom-footer {
    text-align: center;
    margin-top: 3.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
    font-size: 0.72rem;
    color: var(--text-muted);
    letter-spacing: 0.5px;
}
.custom-footer strong { color: var(--text-secondary); font-weight: 600; }

/* ── Responsive ──────────────────────────────────────────────────── */
@media (max-width: 480px) {
    .block-container { padding: 0 0.8rem 5rem !important; }
    .app-title { font-size: 2rem; }
    .result-card { padding: 1rem; }
    .score-number { font-size: 3rem; }
    .dilemme-scores { grid-template-columns: 1fr; }
    div.stButton > button:first-child { padding: 0.85rem 1.5rem !important; }
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 7 — HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="app-header">
    <p class="app-eyebrow">Analyse vestimentaire par IA · Gratuit &amp; Premium</p>
    <h1 class="app-title">Juge <em>Mon</em><br>Style</h1>
    <p class="app-subtitle">
        Un regard expert, bienveillant et personnalisé sur votre tenue —
        comme si votre meilleur(e) ami(e) était styliste.
    </p>
</div>
<hr class="header-divider">
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 8 — BANNIÈRE POST-PAIEMENT
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.a_paye:
    st.markdown("""
<div class="payment-success-banner">
    <div class="check">✓</div>
    <h3>Paiement confirmé</h3>
    <p>Uploadez votre photo ci-dessous — le Roast arrive dans les secondes qui suivent.</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 9 — INTERFACE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

# ── 9a. Choix du mode ─────────────────────────────────────────────────────────
st.markdown('<span class="section-label">Mode d\'analyse</span>', unsafe_allow_html=True)
mode = st.radio(
    label="Mode d'analyse",
    options=[
        "✦ Analyse Styliste — Gratuit",
        "⚡ Roast Vestimentaire — 1,50 €",
    ],
    index=1 if st.session_state.a_paye else 0,
    label_visibility="collapsed",
)
is_roast = "Roast" in mode

# ── 9b. Upload(s) ─────────────────────────────────────────────────────────────
st.markdown('<span class="section-label">Votre tenue</span>', unsafe_allow_html=True)

col_a, col_b = st.columns(2, gap="small")
with col_a:
    uploaded_a = st.file_uploader(
        "Tenue A",
        type=["png", "jpg", "jpeg"],
        key="upload_a",
        label_visibility="visible",
    )
    # Sauvegarde de l'image avant redirection Stripe
    if uploaded_a is not None:
        st.session_state.saved_image = uploaded_a.read()
        uploaded_a.seek(0)  # rembobine pour que Image.open() fonctionne ensuite
with col_b:
    uploaded_b = st.file_uploader(
        "Tenue B  *(optionnel — mode Dilemme)*",
        type=["png", "jpg", "jpeg"],
        key="upload_b",
        label_visibility="visible",
    )

# Récupération de l'image sauvegardée si le file_uploader est vide au retour de Stripe
if uploaded_a is None and st.session_state.saved_image is not None:
    uploaded_a = io.BytesIO(st.session_state.saved_image)

has_a = uploaded_a is not None
has_b = uploaded_b is not None
is_dilemme = has_a and has_b and not is_roast  # Dilemme : 2 photos, mode non-Roast

# ── 9c. Situation ─────────────────────────────────────────────────────────────
st.markdown('<span class="section-label">Occasion</span>', unsafe_allow_html=True)

situation_index = 0
try:
    pill_choix = st.pills(
        label="Situation",
        options=SITUATION_LABELS,
        selection_mode="single",
        default=SITUATION_LABELS[0],
        label_visibility="collapsed",
    )
    if pill_choix is None:
        pill_choix = SITUATION_LABELS[0]
    situation_index = SITUATION_LABELS.index(pill_choix)
except AttributeError:
    pill_choix = st.selectbox(
        label="Situation",
        options=SITUATION_LABELS,
        label_visibility="collapsed",
    )
    situation_index = SITUATION_LABELS.index(pill_choix)

situation_choisie = SITUATIONS[situation_index]
situation_desc = situation_choisie["desc"]

# ── 9d. Intention de style ────────────────────────────────────────────────────
st.markdown('<span class="section-label">Intention de style *(optionnel)*</span>', unsafe_allow_html=True)
intention = st.text_input(
    label="Intention",
    placeholder="Ex : paraître professionnel mais accessible, affirmer ma personnalité, affiner ma silhouette…",
    label_visibility="collapsed",
    max_chars=200,
)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 10 — APERÇU & CTA
# ══════════════════════════════════════════════════════════════════════════════

if has_a:
    image_a = Image.open(uploaded_a)
    image_a = ImageOps.exif_transpose(image_a)

    image_b = None
    if has_b:
        image_b = Image.open(uploaded_b)
        image_b = ImageOps.exif_transpose(image_b)

    # Aperçu
    st.markdown("")
    if is_dilemme:
        prev_a, prev_b = st.columns(2, gap="small")
        with prev_a:
            st.image(image_a, caption="Tenue A", use_container_width=True)
        with prev_b:
            st.image(image_b, caption="Tenue B", use_container_width=True)
    else:
        st.image(image_a, caption="Votre tenue", use_container_width=True)

    # Info mode Dilemme
    if is_dilemme:
        st.info("**Mode Dilemme activé** — Deux tenues détectées. L'IA va comparer et choisir pour vous.", icon="⚡")

    # ── Affichage du compteur d'analyses restantes (mode gratuit uniquement) ──
    if not is_roast:
        restantes = analyses_restantes()
        if restantes > 0:
            st.caption(f"✦ {restantes} analyse(s) gratuite(s) restante(s) aujourd'hui")
        else:
            st.warning(
                "🌙 Vous avez utilisé vos 3 analyses gratuites du jour. "
                "Revenez demain pour de nouvelles analyses — ou passez au **Mode Roast** pour une analyse pimentées !",
                icon="⏳",
            )

    # CTA
    lancer_analyse = False
    if not is_roast:
        # On n'affiche le bouton que si la limite n'est pas atteinte
        if peut_analyser():
            label_btn = "Comparer les deux tenues" if is_dilemme else "Analyser ma tenue"
            if st.button(f"✦  {label_btn.upper()}"):
                lancer_analyse = True
    else:
        if st.session_state.a_paye:
            # Déclenchement automatique après retour de Stripe si photo disponible
            if st.session_state.auto_roast and has_a:
                st.session_state.auto_roast = False
                lancer_analyse = True
            elif st.button("⚡  LANCER LE ROAST"):
                lancer_analyse = True
        else:
            st.markdown(f"""
<div class="stripe-btn-wrapper">
    <a href="{STRIPE_LINK}" class="stripe-btn" target="_blank" rel="noopener noreferrer">
        Payer 1,50 € et accéder au Roast
    </a>
    <p class="stripe-sub">Paiement sécurisé par Stripe · Résultat immédiat</p>
</div>
""", unsafe_allow_html=True)


    # ══════════════════════════════════════════════════════════════════════════
    #  SECTION 10d — ANALYSE IA
    # ══════════════════════════════════════════════════════════════════════════

    if lancer_analyse:

        spinner_msg = (
            "Comparaison des deux tenues en cours…" if is_dilemme
            else "Analyse de votre tenue en cours…" if not is_roast
            else "Le verdict est en préparation…"
        )

        with st.spinner(spinner_msg):

            # 1. Compression de l'image
            images_b64 = [compress_image_to_base64(image_a)]
            if is_dilemme:
                images_b64.append(compress_image_to_base64(image_b))

            # 2. Sélection du mode de prompt
            prompt_mode = "dilemme" if is_dilemme else ("roast" if is_roast else "drip")
            prompt = construire_prompt(prompt_mode, situation_desc, intention)

            try:
                # 3. Appel OpenAI Vision
                reponse_brute = appeler_openai(prompt, images_b64)

                # 4. Extraction CoT + parsing
                reflexion_text, reponse_propre = extraire_reflexion(reponse_brute)
                r = parser_reponse(reponse_propre)

                # 5. Consommation crédit et compteur — déplacés après le check visibilité
                # (voir dans chaque branche d'affichage ci-dessous)

                # ── GESTION ERREUR VISIBILITÉ ──────────────────────────────
                if r["visibilite"].startswith("erreur"):
                    message_ia = r.get("description") or r["visibilite"].replace("erreur:", "").strip()
                    titre_err = "Photo insuffisante" if not is_roast else "Photo irrecevable"
                    icone_err = "📷" if not is_roast else "🔍"
                    st.markdown(
                        f'<div class="visibility-error">'
                        f'<div class="ve-icon">{icone_err}</div>'
                        f'<div class="ve-title">{titre_err}</div>'
                        f'<div class="ve-body">{message_ia}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                # ── MODE DILEMME ───────────────────────────────────────────
                elif r.get("mode") == "dilemme":

                    # Consommation crédit (uniquement si succès)
                    if is_roast and st.session_state.a_paye:
                        st.session_state.a_paye = False
                    if not is_roast:
                        incrementer_compteur()

                    # Badge occasion
                    st.markdown(
                        f'<div class="context-badge">{situation_choisie["emoji"]} '
                        f'{situation_choisie["label"]}</div>',
                        unsafe_allow_html=True,
                    )

                    # ── FIX BUG : scores A vs B construits sans f-strings imbriquées ──
                    # On calcule d'abord toutes les valeurs conditionnelles AVANT la f-string
                    gagnante = r.get("gagnante", "A").upper()

                    # Tenue A
                    cell_a_class = "dilemme-score-cell winner" if gagnante == "A" else "dilemme-score-cell"
                    label_a = "Tenue A ✓ Gagnante" if gagnante == "A" else "Tenue A"
                    badge_a = '<div class="winner-badge">Recommandée</div>' if gagnante == "A" else ""

                    # Tenue B
                    cell_b_class = "dilemme-score-cell winner" if gagnante == "B" else "dilemme-score-cell"
                    label_b = "Tenue B ✓ Gagnante" if gagnante == "B" else "Tenue B"
                    badge_b = '<div class="winner-badge">Recommandée</div>' if gagnante == "B" else ""

                    score_a = r.get("score_a", "?")
                    score_b = r.get("score_b", "?")

                    # Construction HTML propre sans guillemets imbriqués
                    html_scores = (
                        '<div class="dilemme-scores">'
                        f'<div class="{cell_a_class}">'
                        f'<div class="dilemme-score-label">{label_a}</div>'
                        f'<div class="dilemme-score-value">{score_a}</div>'
                        f'{badge_a}'
                        '</div>'
                        f'<div class="{cell_b_class}">'
                        f'<div class="dilemme-score-label">{label_b}</div>'
                        f'<div class="dilemme-score-value">{score_b}</div>'
                        f'{badge_b}'
                        '</div>'
                        '</div>'
                    )
                    st.markdown(html_scores, unsafe_allow_html=True)

                    # Descriptions A et B
                    if r.get("desc_a"):
                        label_genre = r.get("genre", "neutre")
                        symbole_genre = "♂" if label_genre == "masculin" else ("♀" if label_genre == "feminin" else "◈")
                        badge_html = (
                            f'<span class="genre-badge genre-{label_genre}">'
                            f'{symbole_genre} style {label_genre}</span>'
                        )
                        st.markdown(
                            f'<div class="desc-card">'
                            f'<div class="desc-card-header">Tenue A — détail{badge_html}</div>'
                            f'<div class="desc-card-body">{r["desc_a"]}</div>'
                            f'</div>'
                            f'<div class="desc-card" style="margin-top:0.5rem">'
                            f'<div class="desc-card-header">Tenue B — détail</div>'
                            f'<div class="desc-card-body">{r["desc_b"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                    # Analyse comparative
                    st.success(f"**Analyse comparative**\n\n{r['analyse']}")

                    # Card affiliation
                    if r.get("accessoire") and r["accessoire"] in AFFILIATE_CATALOG:
                        prod = AFFILIATE_CATALOG[r["accessoire"]]
                        affil_html = (
                            '<div style="margin-top:1rem;">'
                            f'<a href="{prod["affiliate_url"]}" target="_blank" rel="noopener noreferrer sponsored" class="affil-card">'
                            f'<div class="affil-emoji">{prod["emoji"]}</div>'
                            '<div class="affil-body">'
                            '<div class="affil-header">Notre sélection</div>'
                            f'<div class="affil-name">{prod["name"]}</div>'
                            f'<div class="affil-tagline">{prod["tagline"]}</div>'
                            '</div>'
                            '<div class="affil-cta">Voir →</div>'
                            '</a>'
                            '</div>'
                        )
                        st.markdown(affil_html, unsafe_allow_html=True)

                    # ── Bouton Story (mode Dilemme) ────────────────────────
                    # Pour le dilemme, on génère la story avec la tenue gagnante
                    image_story = image_a if gagnante == "A" else (image_b or image_a)
                    score_story = score_a if gagnante == "A" else score_b
                    titre_story = f"Tenue {gagnante} recommandée"
                    story_bytes = generer_story(image_story, score_story, titre_story, r["analyse"])
                    st.download_button(
                        label="📲 Télécharger ma Story Instagram / TikTok",
                        data=story_bytes,
                        file_name="juge_mon_style_story.jpg",
                        mime="image/jpeg",
                        key="dl_story_dilemme",
                    )

                # ── MODE DRIP (analyse classique) ──────────────────────────
                elif r.get("mode") in ("drip", None) and not is_roast:

                    # Consommation crédit (uniquement si succès)
                    if not is_roast:
                        incrementer_compteur()

                    # Badge occasion
                    st.markdown(
                        f'<div class="context-badge">{situation_choisie["emoji"]} '
                        f'{situation_choisie["label"]}</div>',
                        unsafe_allow_html=True,
                    )

                    # Card description
                    if r.get("description"):
                        label_genre = r.get("genre", "neutre")
                        symbole_genre = "♂" if label_genre == "masculin" else ("♀" if label_genre == "feminin" else "◈")
                        badge_html = (
                            f'<span class="genre-badge genre-{label_genre}">'
                            f'{symbole_genre} style {label_genre}</span>'
                        )
                        st.markdown(
                            f'<div class="desc-card">'
                            f'<div class="desc-card-header">Ce que l\'IA voit{badge_html}</div>'
                            f'<div class="desc-card-body">{r["description"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                    # Score
                    st.markdown(
                        f'<div class="score-block">'
                        f'<div class="score-number">{r["score"]}</div>'
                        f'<div class="score-label">Score de style</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    # Verdict
                    corps = f"**{r['titre']}**\n\n{r['analyse']}"
                    if r.get("conseil"):
                        corps += f"\n\n💡 *{r['conseil']}*"
                    st.success(corps)

                    # Card affiliation
                    if r.get("accessoire") and r["accessoire"] in AFFILIATE_CATALOG:
                        prod = AFFILIATE_CATALOG[r["accessoire"]]
                        affil_html = (
                            '<div style="margin-top:1rem;">'
                            f'<a href="{prod["affiliate_url"]}" target="_blank" rel="noopener noreferrer sponsored" class="affil-card">'
                            f'<div class="affil-emoji">{prod["emoji"]}</div>'
                            '<div class="affil-body">'
                            '<div class="affil-header">Notre sélection</div>'
                            f'<div class="affil-name">{prod["name"]}</div>'
                            f'<div class="affil-tagline">{prod["tagline"]}</div>'
                            '</div>'
                            '<div class="affil-cta">Voir →</div>'
                            '</a>'
                            '</div>'
                        )
                        st.markdown(affil_html, unsafe_allow_html=True)

                    # ── Bouton Story (mode Drip) ───────────────────────────
                    story_bytes = generer_story(
                        image_a,
                        r.get("score", "?"),
                        r.get("titre", "Mon Style"),
                        r.get("analyse", ""),
                    )
                    st.download_button(
                        label="📲 Télécharger ma Story Instagram / TikTok",
                        data=story_bytes,
                        file_name="juge_mon_style_story.jpg",
                        mime="image/jpeg",
                        key="dl_story_drip",
                    )

                # ── MODE ROAST ─────────────────────────────────────────────
                else:

                    # Consommation crédit Roast (uniquement si succès)
                    if is_roast and st.session_state.a_paye:
                        st.session_state.a_paye = False

                    # Badge occasion
                    st.markdown(
                        f'<div class="context-badge">{situation_choisie["emoji"]} '
                        f'{situation_choisie["label"]}</div>',
                        unsafe_allow_html=True,
                    )

                    # Description (ton sarcastique)
                    if r.get("description"):
                        label_genre = r.get("genre", "neutre")
                        symbole_genre = "♂" if label_genre == "masculin" else ("♀" if label_genre == "feminin" else "◈")
                        badge_html = (
                            f'<span class="genre-badge genre-{label_genre}">'
                            f'{symbole_genre} style {label_genre}</span>'
                        )
                        st.markdown(
                            f'<div class="desc-card">'
                            f'<div class="desc-card-header">Ce que l\'IA voit{badge_html}</div>'
                            f'<div class="desc-card-body">{r["description"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                    # Score
                    st.markdown(
                        f'<div class="score-block">'
                        f'<div class="score-number">{r["score"]}</div>'
                        f'<div class="score-label">Score de style</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    # Roast
                    corps = f"**{r['titre']}**\n\n{r['analyse']}"
                    if r.get("conseil"):
                        corps += f"\n\n*{r['conseil']}*"
                    st.error(corps)

                    # Pas de Story pour le mode Roast (le contenu est payant)

                # ── CoT expander (tous modes) ──────────────────────────────
                if reflexion_text:
                    with st.expander("Voir le raisonnement de l'IA"):
                        st.markdown(reflexion_text)

            except Exception as e:
                st.error(
                    "Une erreur est survenue lors de la connexion à l'IA. "
                    "Vérifiez que votre compte OpenAI dispose bien de crédit."
                )


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 11 — FOOTER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="custom-footer">
    <strong>Juge Mon Style</strong> · Analyse vestimentaire par IA · Tous droits réservés
</div>
""", unsafe_allow_html=True)
