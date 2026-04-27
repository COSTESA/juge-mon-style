"""
╔══════════════════════════════════════════════════════════════════╗
║               🔥  JUGE MON STYLE  —  app.py                     ║
║   Analyse vestimentaire IA · Contexte · Chain of Thought        ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ─── IMPORTS ──────────────────────────────────────────────────────────────────
import io
import re
import base64

import streamlit as st
from PIL import Image
from openai import OpenAI


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 0 — CONFIG PAGE  (doit être le 1er appel Streamlit)
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Juge Mon Style 📸",
    page_icon="🔥",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════

STRIPE_LINK = "https://buy.stripe.com/test_14A00i1Qhcox7nI9qV77O00"  # ← remplace par ton vrai lien
# Stripe Dashboard → Payment Link → URL de confirmation :
#   https://ton-app.streamlit.app/?payment=success

# Situations contextuelles : emoji · label · description injectée dans le prompt
SITUATIONS = [
    {
        "emoji": "📚",
        "label": "Cours",
        "desc": "une longue journée de cours — il faut avoir l'air réveillé et stylé, tout en faisant croire qu'on a enfilé ça sans effort à 7h du mat",
    },
    {
        "emoji": "💻",
        "label": "Journée de taf",
        "desc": "une journée classique au travail ou en stage — l'objectif est d'avoir l'air professionnel et sérieux, tout en gardant son flow personnel",
    },
    {
        "emoji": "🏋️",
        "label": "Séance de sport",
        "desc": "aller transpirer à la salle de sport ou courir dehors — la tenue doit être technique, confortable, mais assez propre pour croiser son crush entre deux machines",
    },
    {
        "emoji": "🍷",
        "label": "Dîner chic",
        "desc": "un dîner dans un endroit un peu chic — on sort les belles pièces, il faut être élégant, clean, et ne pas faire tâche dans le décor",
    },
    {
        "emoji": "🛋️",
        "label": "Chill entre potes",
        "desc": "traîner en ville ou se poser chez des amis — le confort est roi, mais le 'drip' doit rester suffisant pour ne pas se faire vanner par le groupe",
    },
    {
        "emoji": "🛒",
        "label": "Faire les courses",
        "desc": "la mission rapide au supermarché du coin — le test ultime entre le look 'streetwear décontracté' réussi et l'effet 'je suis sorti en pyjama'",
    },
    {
        "emoji": "💘",
        "label": "Premier date",
        "desc": "un premier rendez-vous romantique — l'enjeu est critique, il faut faire une excellente impression sans donner l'air d'avoir passé 3 heures devant le miroir",
    },
    {
        "emoji": "🪩",
        "label": "Soirée / Bar",
        "desc": "sortir boire un verre ou aller en club — il faut une tenue qui a de l'allure dans la pénombre, qui résiste à la chaleur, et qui attire l'œil",
    },
    {
        "emoji": "💼",
        "label": "Entretien d'embauche",
        "desc": "un entretien d'embauche dans une boîte parisienne — il faut paraître sérieux, compétent, et ne surtout pas faire de faute de goût rédhibitoire",
    },
    {
        "emoji": "⛺",
        "label": "Week-end camping",
        "desc": "un week-end camping dans la forêt avec des amis — utilité > esthétique, mais ça ne veut pas dire qu'on peut s'habiller comme une poubelle",
    },
    {
        "emoji": "🍽️",
        "label": "Repas de famille",
        "desc": "un repas de famille dominical chez des parents bourgeois et légèrement coincés — ni trop casual, ni trop extravagant, sous peine de commentaires passif-agressifs",
    },
    {
        "emoji": "🎪",
        "label": "Festival",
        "desc": "un festival de musique en plein air — créativité maximale autorisée, chaleur garantie, confort essentiel, et tout le monde est là pour se montrer",
    },
]

SITUATION_LABELS = [f"{s['emoji']} {s['label']}" for s in SITUATIONS]

# ── Catalogue d'affiliation ────────────────────────────────────────────────
# Chaque entrée : id (clé unique que l'IA renvoie), name, emoji, affiliate_url.
# Pour ajouter un produit : copier un bloc, changer l'id et les infos.
AFFILIATE_CATALOG = {
    "chain_argent": {
        "name": "Chaîne en argent",
        "emoji": "🔗",
        "tagline": "Le détail qui change tout",
        "affiliate_url": "https://www.example.com/chain-argent?ref=jugmonstyle",
    },
    "sneakers_blanches": {
        "name": "Sneakers blanches",
        "emoji": "👟",
        "tagline": "La base de toute bonne tenue",
        "affiliate_url": "https://www.example.com/sneakers-blanches?ref=jugmonstyle",
    },
    "casquette_minimale": {
        "name": "Casquette minimaliste",
        "emoji": "🧢",
        "tagline": "Structure et attitude en un geste",
        "affiliate_url": "https://www.example.com/casquette-minimale?ref=jugmonstyle",
    },
    "veste_oversize": {
        "name": "Veste oversize",
        "emoji": "🧥",
        "tagline": "La pièce qui structure tout",
        "affiliate_url": "https://www.example.com/veste-oversize?ref=jugmonstyle",
    },
    "sac_tote": {
        "name": "Tote bag en canvas",
        "emoji": "🛍️",
        "tagline": "Cool, sobre, fonctionnel",
        "affiliate_url": "https://www.example.com/tote-bag?ref=jugmonstyle",
    },
    "lunettes_soleil": {
        "name": "Lunettes de soleil",
        "emoji": "🕶️",
        "tagline": "L'accessoire qui ferme les débats",
        "affiliate_url": "https://www.example.com/lunettes-soleil?ref=jugmonstyle",
    },
}

# Ligne de catalogue injectée dans le prompt (générée une fois, réutilisée)
_CATALOG_LINES = "\n".join(
    f"  - {k} → {v['name']}" for k, v in AFFILIATE_CATALOG.items()
)
_CATALOG_KEYS = ", ".join(AFFILIATE_CATALOG.keys())


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — INITIALISATION CLIENT OPENAI
# ══════════════════════════════════════════════════════════════════════════════

try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.error(
        "⚠️ Clé API introuvable. "
        "Vérifie que ton fichier `.streamlit/secrets.toml` existe et contient `OPENAI_API_KEY`."
    )
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════

def compress_image_to_base64(pil_image, max_dimension=512, quality=60):
    """
    Redimensionne à max 512x512 px et compresse en JPEG qualité 60.
    detail=low → 85 tokens fixes (économie ~-95 % de coût image).
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


def appeler_openai(base64_image, prompt):
    """Envoie image + prompt à OpenAI Vision. Retourne la réponse brute."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "low",
                        },
                    },
                ],
            }
        ],
    )
    return response.choices[0].message.content


def extraire_reflexion(reponse_brute):
    """
    Sépare le bloc <reflexion>...</reflexion> du reste.
    Retourne (reflexion_text, reponse_propre).
    """
    pattern = re.compile(r"<reflexion>(.*?)</reflexion>", re.DOTALL | re.IGNORECASE)
    match = pattern.search(reponse_brute)
    reflexion_text = match.group(1).strip() if match else ""
    reponse_propre = pattern.sub("", reponse_brute).strip()
    return reflexion_text, reponse_propre


def parser_reponse(reponse_propre):
    """
    Parse la réponse au format complet (7 champs) :
      visibilite | genre | description | score | titre | analyse | conseil | accessoire_id

    Retourne un dict avec les clés correspondantes.
    - visibilite : "ok" ou "erreur:<raison>"
    - genre      : "masculin", "feminin", ou "neutre"
    - description: paragraphe descriptif de la tenue (preuve par l'image)
    - score      : ex. "7/10"
    - titre      : nom du style (3-4 mots)
    - analyse    : verdict expert 2-3 phrases
    - conseil    : conseil actionnable
    - accessoire : clé du catalogue ou "" (mode Drip) / toujours "" en Roast
    """
    parties = [p.strip() for p in reponse_propre.split("|")]

    def get(i, defaut=""):
        return parties[i] if len(parties) > i else defaut

    visibilite  = get(0, "ok")
    genre       = get(1, "neutre").lower()
    description = get(2, "")
    score       = get(3, "?/10")
    titre       = get(4, "Analyse")
    analyse     = get(5, reponse_propre)
    conseil     = get(6, "")
    accessoire  = get(7, "")

    # Normalisation genre
    if genre not in ("masculin", "feminin", "neutre"):
        genre = "neutre"

    # Normalisation accessoire
    if accessoire.lower() in ("none", "aucun", ""):
        accessoire = ""

    return {
        "visibilite":  visibilite,
        "genre":       genre,
        "description": description,
        "score":       score,
        "titre":       titre,
        "analyse":     analyse,
        "conseil":     conseil,
        "accessoire":  accessoire,
    }


def construire_prompt(is_roast, situation_desc):
    """Injecte le contexte de situation (+ catalogue affiliation pour Drip) dans le prompt."""
    if not is_roast:
        return PROMPT_DRIP_TEMPLATE.format(
            situation=situation_desc,
            catalog_lines=_CATALOG_LINES,
            catalog_keys=_CATALOG_KEYS,
        )
    return PROMPT_ROAST_TEMPLATE.format(situation=situation_desc)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — TEMPLATES DE PROMPTS (CoT + contexte dynamique)
# ══════════════════════════════════════════════════════════════════════════════

PROMPT_DRIP_TEMPLATE = """Tu es "Maxime Leclair", Directeur Artistique de mode parisien avec 15 ans d'expérience entre les rédactions de Vogue, les castings de fashion week et les studios de streetwear. Tu as l'oeil absolu — et l'honnêteté d'un chirurgien.

━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTE DE LA SITUATION :
L'utilisateur porte cette tenue pour : {situation}.
Ton analyse doit être entièrement ancrée dans ce contexte.
━━━━━━━━━━━━━━━━━━━━━━━━━━

CATALOGUE D'ACCESSOIRES DISPONIBLES :
{catalog_lines}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROCESSUS D'ANALYSE EN 6 ÉTAPES (Chain of Thought) :
Tu dois réfléchir dans une balise <reflexion> AVANT de produire ton verdict public.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ÉTAPE 1 — VÉRIFICATION DE VISIBILITÉ :
Évalue honnêtement si tu peux réellement analyser la tenue :
  - Voit-on le corps en entier ou au moins du buste aux pieds ?
  - L'image est-elle suffisamment lumineuse et nette ?
  - La tenue n'est-elle pas cachée (trench fermé, angle de dos uniquement, plan trop serré sur le visage) ?
→ Si la tenue est clairement visible : note "ok".
→ Si tu ne peux pas faire une vraie analyse : note "erreur" et explique brièvement POURQUOI (ex: selfie de visage, trop sombre, image coupée sous la taille).

ÉTAPE 2 — DÉTECTION DU GENRE DE PRÉSENTATION :
Observe les codes vestimentaires visibles (coupes, pièces, palette, silhouette) et détermine si la personne présente un style :
  - "masculin" : codes classiquement masculins (pantalon droit, chemise, costume, etc.)
  - "feminin" : codes classiquement féminins (robe, jupe, décolleté, etc.)
  - "neutre" : codes mixtes, androgyne, ou impossible à catégoriser
→ Cette détection sert UNIQUEMENT à adapter tes pronoms et ton vocabulaire, pas à juger.

ÉTAPE 3 — INVENTAIRE PRÉCIS :
Liste méthodiquement chaque pièce visible : type exact, couleur précise (pas juste "bleu" — "bleu marine", "cobalt", "ciel"), matière apparente, et coupe.

ÉTAPE 4 — ANALYSE STYLISTIQUE :
  - Silhouette et proportions globales
  - Colorimétrie (harmonie, contraste, rappels entre pièces)
  - Adéquation avec "{situation}"
  - Point fort dominant et point faible principal

ÉTAPE 5 — CHOIX DE L'ACCESSOIRE :
Parmi le catalogue disponible, lequel élève le mieux cette tenue pour ce contexte ? Justifie en une phrase.

ÉTAPE 6 — VERDICT PRÉLIMINAIRE :
Note sur 10, titre du style (3-4 mots), angle du conseil.

<reflexion> contient tout ce travail — elle N'APPARAÎT PAS dans le verdict public.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERDICT PUBLIC (après </reflexion>) :
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Si ÉTAPE 1 = erreur → réponds UNIQUEMENT avec ce format (3 champs seulement) :
erreur:[raison courte et directe] | neutre | [Message bienveillant à l'utilisateur : explique ce qui ne va pas dans la photo et comment retenter, en 1-2 phrases — sans inventer de tenue]

Si ÉTAPE 1 = ok → réponds UNIQUEMENT avec ce format (8 champs), séparés par des | :
ok | [masculin/feminin/neutre] | [Description détaillée de la tenue en 3-4 phrases — ce que tu vois EXACTEMENT : chaque pièce, sa couleur précise, sa matière apparente, sa coupe, et comment les éléments s'articulent entre eux. L'utilisateur doit se dire "l'IA a vraiment tout vu".] | [Note]/10 | [Nom du style en 3-4 mots] | [Analyse experte 2-3 phrases, contexte inclus, pronoms adaptés au genre détecté] | [Conseil d'élévation précis et actionnable] | [Identifiant exact du catalogue ou "none"]

RÈGLES ABSOLUES :
- Champ 8 : uniquement parmi {catalog_keys} ou "none". Jamais d'identifiant inventé.
- Ne rien écrire en dehors du format demandé après </reflexion>.
- En cas d'erreur de visibilité : ne jamais inventer ou deviner la tenue.
"""

PROMPT_ROAST_TEMPLATE = """Tu es "Le Commissaire du Mauvais Goût", critique vestimentaire légendaire, sans filtre, sans pitié. Tu as le flair d'un chasseur de tendances et la langue d'un chroniqueur Gen Z qui a grandi sur Twitter.

━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTE DE LA SITUATION :
La personne porte CETTE tenue pour : {situation}.
Exploite l'inadéquation entre la tenue et ce contexte — c'est là que les meilleures punchlines naissent.
━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROCESSUS D'ANALYSE EN 6 ÉTAPES (Chain of Thought) :
Tu dois réfléchir dans une balise <reflexion> AVANT de produire ton verdict public.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ÉTAPE 1 — VÉRIFICATION DE VISIBILITÉ :
Évalue honnêtement si tu peux réellement analyser la tenue :
  - Voit-on le corps en entier ou au moins du buste aux pieds ?
  - L'image est-elle suffisamment lumineuse et nette ?
  - La tenue n'est-elle pas cachée (trench fermé, angle de dos uniquement, plan trop serré sur le visage) ?
→ Si la tenue est clairement visible : note "ok".
→ Si tu ne peux pas faire une vraie analyse : note "erreur" et explique brièvement POURQUOI (ex: selfie de visage, trop sombre, image coupée sous la taille).

ÉTAPE 2 — DÉTECTION DU GENRE DE PRÉSENTATION :
Détermine "masculin", "feminin" ou "neutre" selon les codes vestimentaires visibles.
Adapte tes pronoms et références en conséquence dans le Roast.

ÉTAPE 3 — INVENTAIRE DES CRIMES :
Liste méthodiquement chaque pièce : type, couleur exacte, matière, coupe — et le problème principal de chacune.

ÉTAPE 4 — HIÉRARCHIE DES HORREURS :
Identifie LE pire élément (le cœur du Roast) et classe les autres par ordre décroissant d'horreur stylistique.

ÉTAPE 5 — ANGLE D'ATTAQUE CONTEXTUEL :
Comment "{situation}" amplifie-t-il le désastre ? Cherche l'angle le plus absurde et percutant.

ÉTAPE 6 — ARSENAL DE PUNCHLINES :
Brainstorme 2-3 comparaisons ridicules (personnes, lieux, situations, films). Retiens la plus dévastatrice. Rédige la sentence finale (courte, mortelle, mémorable).

<reflexion> contient tout ce travail — elle N'APPARAÎT PAS dans le verdict public.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERDICT PUBLIC (après </reflexion>) :
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Si ÉTAPE 1 = erreur → réponds UNIQUEMENT avec ce format (3 champs) :
erreur:[raison courte] | neutre | [Message sarcastique mais clair : explique ce qui ne va pas dans la photo, en 1-2 phrases — le Commissaire est agacé qu'on lui soumette une photo illisible]

Si ÉTAPE 1 = ok → réponds UNIQUEMENT avec ce format (7 champs), séparés par des | :
ok | [masculin/feminin/neutre] | [Description précise de la tenue en 3-4 phrases — chaque pièce, sa couleur exacte, sa matière, sa coupe. Ton peut être légèrement sarcastique dès ici.] | [Note]/10 | [Titre humiliant en 3-4 mots] | [Le Roast — 2-3 phrases percutantes, contexte exploité, comparaisons incluses, pronoms adaptés au genre] | [Sentence finale — une punchline courte et mortelle]

RÈGLES ABSOLUES :
- Ne rien écrire en dehors du format demandé après </reflexion>.
- En cas d'erreur de visibilité : ne jamais inventer ou deviner la tenue. Le Commissaire refuse de travailler dans le noir.
"""


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — GESTION DE L'ÉTAT (Session State & Query Params)
# ══════════════════════════════════════════════════════════════════════════════

if "a_paye" not in st.session_state:
    st.session_state.a_paye = False

payment_param = st.query_params.get("payment", "")
if payment_param == "success" and not st.session_state.a_paye:
    st.session_state.a_paye = True
    st.query_params.clear()
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 6 — CSS PERSONNALISÉ
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background-color: #0A0A0F !important;
    color: #F0F0F0;
    font-family: 'DM Sans', sans-serif;
}

#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="collapsedControl"] { display: none !important; }

[data-testid="stMain"] > div:first-child { padding-top: 2rem !important; }
.block-container {
    max-width: 520px !important;
    padding: 1.5rem 1.2rem 4rem !important;
    margin: 0 auto;
}

.app-header { text-align: center; padding: 1.8rem 1rem 1rem; }
.app-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2.4rem, 10vw, 3.4rem);
    font-weight: 800;
    line-height: 1.1;
    background: linear-gradient(135deg, #FE2C55 0%, #ff6b35 40%, #25F4EE 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -1px;
    margin-bottom: 0.4rem;
}
.app-subtitle {
    font-size: clamp(0.9rem, 3.5vw, 1.05rem);
    color: #888;
    font-weight: 400;
    line-height: 1.5;
    margin-top: 0;
}
.neon-divider {
    height: 2px;
    background: linear-gradient(90deg, transparent, #FE2C55, #25F4EE, transparent);
    border: none;
    margin: 1.6rem 0;
    opacity: 0.6;
}

[data-testid="stFileUploader"] {
    background: #13131A !important;
    border: 1.5px dashed #2a2a3a !important;
    border-radius: 20px !important;
    padding: 1rem !important;
    transition: border-color 0.3s ease;
}
[data-testid="stFileUploader"]:hover { border-color: #FE2C55 !important; }
[data-testid="stFileUploader"] label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem !important;
    color: #aaa !important;
}
[data-testid="stFileUploaderDropzone"] { background: transparent !important; border: none !important; }

.result-card {
    background: #13131A;
    border: 1px solid #1E1E2E;
    border-radius: 24px;
    padding: 1.2rem;
    margin-top: 1rem;
}

[data-testid="stImage"] img {
    border-radius: 16px !important;
    object-fit: cover;
    width: 100%;
    max-height: 380px;
}
[data-testid="stImage"] > div > p {
    font-size: 0.75rem !important;
    color: #555 !important;
    text-align: center;
    margin-top: 0.4rem;
}

.mode-label {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #F0F0F0;
    margin-bottom: 0.8rem;
    display: block;
}
.section-label {
    font-family: 'Syne', sans-serif;
    font-size: 0.85rem;
    font-weight: 700;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin: 1.4rem 0 0.6rem;
    display: block;
}

[data-testid="stRadio"] > div { gap: 0.6rem !important; flex-direction: column !important; }
[data-testid="stRadio"] label {
    background: #0E0E18 !important;
    border: 1.5px solid #222235 !important;
    border-radius: 14px !important;
    padding: 0.75rem 1rem !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    color: #ccc !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
    width: 100% !important;
}
[data-testid="stRadio"] label:hover { border-color: #FE2C55 !important; color: #fff !important; background: #1a0d14 !important; }
[data-testid="stRadio"] label:has(input:checked) {
    border-color: #FE2C55 !important;
    background: linear-gradient(135deg, #1a0610, #0d1a1a) !important;
    color: #fff !important;
    box-shadow: 0 0 14px rgba(254, 44, 85, 0.18) !important;
}
[data-testid="stRadio"] input[type="radio"] { display: none !important; }

/* Pills natifs Streamlit */
[data-testid="stPills"] { gap: 0.5rem !important; flex-wrap: wrap !important; }
[data-testid="stPills"] button {
    background: #0E0E18 !important;
    border: 1.5px solid #222235 !important;
    border-radius: 50px !important;
    color: #aaa !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
    padding: 0.4rem 0.85rem !important;
    transition: all 0.2s ease !important;
}
[data-testid="stPills"] button:hover { border-color: #25F4EE !important; color: #fff !important; }
[data-testid="stPills"] button[aria-selected="true"],
[data-testid="stPills"] button[data-selected="true"] {
    background: linear-gradient(135deg, #0a1f2b, #0d2b1a) !important;
    border-color: #25F4EE !important;
    color: #25F4EE !important;
    box-shadow: 0 0 10px rgba(37, 244, 238, 0.2) !important;
}

/* Selectbox fallback */
[data-testid="stSelectbox"] > div > div {
    background: #13131A !important;
    border: 1.5px solid #222235 !important;
    border-radius: 14px !important;
    color: #F0F0F0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
    transition: border-color 0.2s ease !important;
}
[data-testid="stSelectbox"] > div > div:hover { border-color: #25F4EE !important; }
[data-testid="stSelectbox"] svg { color: #25F4EE !important; }

div.stButton > button:first-child {
    background: linear-gradient(135deg, #FE2C55 0%, #d4196b 50%, #25F4EE 100%) !important;
    background-size: 200% 200% !important;
    color: #fff !important;
    border: none !important;
    border-radius: 50px !important;
    padding: 1rem 2rem !important;
    font-size: clamp(1rem, 4vw, 1.2rem) !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.5px !important;
    width: 100% !important;
    margin-top: 0.5rem !important;
    transition: all 0.35s cubic-bezier(0.23, 1, 0.32, 1) !important;
    box-shadow: 0 4px 24px rgba(254, 44, 85, 0.25) !important;
    cursor: pointer !important;
    animation: gradientShift 4s ease infinite !important;
}
div.stButton > button:first-child:hover {
    transform: translateY(-3px) scale(1.03) !important;
    box-shadow: 0 10px 36px rgba(254, 44, 85, 0.45) !important;
}
div.stButton > button:first-child:active { transform: translateY(0) scale(0.98) !important; }
@keyframes gradientShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

[data-testid="stSpinner"] p {
    color: #888 !important;
    font-size: 0.9rem !important;
    font-style: italic;
}

[data-testid="stAlert"] {
    border-radius: 18px !important;
    font-size: 1rem !important;
    line-height: 1.6 !important;
    padding: 1.1rem 1.3rem !important;
    margin-top: 0.5rem !important;
}
[data-testid="stAlert"][data-baseweb="notification"] {
    background: #0d1f1a !important;
    border: 1px solid #25F4EE40 !important;
    color: #b8fff8 !important;
}
div[data-testid="stAlert"].st-emotion-cache-x9yi0t,
div[role="alert"].st-emotion-cache-x9yi0t {
    background: #1f0d11 !important;
    border: 1px solid #FE2C5540 !important;
    color: #ffb3c1 !important;
}

.score-block { text-align: center; margin: 1.4rem 0 0.4rem; }
.score-number {
    font-family: 'Syne', sans-serif;
    font-size: 3.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #FE2C55, #25F4EE);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1;
}
.score-label {
    font-size: 0.8rem;
    color: #555;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 0.2rem;
}

/* Expander réflexion CoT */
[data-testid="stExpander"] {
    background: #0C0C15 !important;
    border: 1px solid #25F4EE22 !important;
    border-radius: 16px !important;
    margin-top: 0.8rem !important;
}
[data-testid="stExpander"] summary {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
    color: #25F4EE !important;
    padding: 0.7rem 1rem !important;
}
[data-testid="stExpander"] summary:hover { color: #fff !important; }
[data-testid="stExpander"] > div > div {
    padding: 0 1rem 0.8rem !important;
    font-size: 0.82rem !important;
    color: #777 !important;
    line-height: 1.65 !important;
    font-style: italic;
    white-space: pre-wrap;
}

/* Badge contexte */
.context-badge {
    display: inline-block;
    background: linear-gradient(135deg, #0a1a2b, #0d0a1f);
    border: 1px solid #25F4EE44;
    border-radius: 50px;
    padding: 0.3rem 0.9rem;
    font-size: 0.78rem;
    color: #25F4EE;
    margin-bottom: 1rem;
    font-weight: 500;
}

/* ── Card Description "L'IA a tout vu" ──────────────────────────── */
.desc-card {
    background: #0e0e1a;
    border: 1px solid #ffffff0d;
    border-left: 3px solid #25F4EE;
    border-radius: 16px;
    padding: 1rem 1.2rem;
    margin: 1rem 0 0.6rem;
    position: relative;
}
.desc-card-header {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #25F4EE;
    font-weight: 700;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.desc-card-header::after {
    content: "";
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, #25F4EE22, transparent);
}
.desc-card-body {
    font-size: 0.88rem;
    color: #bbb;
    line-height: 1.7;
    font-style: italic;
}
.genre-badge {
    display: inline-block;
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 700;
    font-style: normal;
    padding: 0.15rem 0.55rem;
    border-radius: 50px;
    margin-left: 0.5rem;
    vertical-align: middle;
}
.genre-masculin  { background: #0a1525; color: #6ab0ff; border: 1px solid #6ab0ff44; }
.genre-feminin   { background: #25091a; color: #ff80b5; border: 1px solid #ff80b544; }
.genre-neutre    { background: #131320; color: #aaa;    border: 1px solid #aaa3; }

/* ── Bloc erreur visibilité ──────────────────────────────────────── */
.visibility-error {
    background: linear-gradient(135deg, #1a0e00, #1a0a0a);
    border: 1px solid #ff8c0044;
    border-radius: 18px;
    padding: 1.3rem 1.5rem;
    text-align: center;
    margin-top: 0.8rem;
}
.visibility-error .ve-icon { font-size: 2.2rem; margin-bottom: 0.5rem; }
.visibility-error .ve-title {
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    color: #ff8c00;
    margin-bottom: 0.4rem;
}
.visibility-error .ve-body {
    font-size: 0.88rem;
    color: #997755;
    line-height: 1.6;
}
.affil-card {
    background: linear-gradient(135deg, #0f0f1e, #13131A);
    border: 1px solid #ffffff14;
    border-radius: 20px;
    padding: 1rem 1.2rem;
    margin-top: 1.2rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    position: relative;
    overflow: hidden;
}
.affil-card::before {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: 20px;
    padding: 1.5px;
    background: linear-gradient(135deg, #FE2C5530, #25F4EE30);
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    pointer-events: none;
}
.affil-emoji {
    font-size: 2.2rem;
    flex-shrink: 0;
    line-height: 1;
}
.affil-body {
    flex: 1;
    min-width: 0;
}
.affil-header {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 1.8px;
    color: #FE2C55;
    font-weight: 700;
    margin-bottom: 0.15rem;
}
.affil-name {
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    color: #F0F0F0;
    line-height: 1.2;
}
.affil-tagline {
    font-size: 0.78rem;
    color: #666;
    margin-top: 0.1rem;
}
.affil-cta {
    display: inline-block;
    background: linear-gradient(135deg, #25F4EE, #00b8b2);
    color: #0A0A0F !important;
    text-decoration: none !important;
    border-radius: 50px;
    padding: 0.45rem 1rem;
    font-family: 'Syne', sans-serif;
    font-size: 0.8rem;
    font-weight: 700;
    white-space: nowrap;
    transition: all 0.25s ease;
    flex-shrink: 0;
}
.affil-cta:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(37, 244, 238, 0.35);
    color: #0A0A0F !important;
    text-decoration: none !important;
}

.stripe-btn-wrapper { margin-top: 0.5rem; }
.stripe-btn {
    display: block;
    width: 100%;
    padding: 1rem 2rem;
    background: linear-gradient(135deg, #FE2C55 0%, #d4196b 50%, #25F4EE 100%);
    background-size: 200% 200%;
    color: #fff !important;
    text-decoration: none !important;
    border-radius: 50px;
    font-family: 'Syne', sans-serif;
    font-size: clamp(1rem, 4vw, 1.2rem);
    font-weight: 700;
    letter-spacing: 0.5px;
    text-align: center;
    box-shadow: 0 4px 24px rgba(254, 44, 85, 0.25);
    transition: all 0.35s cubic-bezier(0.23, 1, 0.32, 1);
    animation: gradientShift 4s ease infinite;
    box-sizing: border-box;
}
.stripe-btn:hover {
    transform: translateY(-3px) scale(1.03);
    box-shadow: 0 10px 36px rgba(254, 44, 85, 0.45);
    color: #fff !important;
    text-decoration: none !important;
}
.stripe-btn:active { transform: translateY(0) scale(0.98); }
.stripe-sub { text-align: center; font-size: 0.72rem; color: #444; margin-top: 0.5rem; }

.payment-success-banner {
    background: linear-gradient(135deg, #0d2b1a, #0a1f2b);
    border: 1px solid #25F4EE55;
    border-radius: 18px;
    padding: 1.2rem 1.4rem;
    text-align: center;
    margin-bottom: 1.2rem;
}
.payment-success-banner .check { font-size: 2rem; margin-bottom: 0.3rem; }
.payment-success-banner h3 {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    color: #25F4EE;
    margin: 0 0 0.3rem;
}
.payment-success-banner p { font-size: 0.85rem; color: #888; margin: 0; }

.custom-footer {
    text-align: center;
    margin-top: 3rem;
    font-size: 0.72rem;
    color: #333;
    letter-spacing: 0.5px;
}
.custom-footer span {
    background: linear-gradient(90deg, #FE2C55, #25F4EE);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 600;
}

@media (max-width: 480px) {
    .block-container { padding: 1rem 0.8rem 5rem !important; }
    .app-title { font-size: 2.4rem; }
    .result-card { padding: 0.9rem; }
    [data-testid="stImage"] img { max-height: 300px; }
    div.stButton > button:first-child { padding: 0.9rem 1.5rem !important; font-size: 1rem !important; }
    .stripe-btn { padding: 0.9rem 1.5rem; font-size: 1rem; }
    .score-number { font-size: 3rem; }
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 7 — HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="app-header">
    <p class="app-title">🔥 Juge Mon Style</p>
    <p class="app-subtitle">L'IA qui n'a aucun filtre.<br>Prêt à te faire tailler&nbsp;? 👇</p>
</div>
<hr class="neon-divider">
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 8 — BANNIÈRE POST-PAIEMENT
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.a_paye:
    st.markdown("""
<div class="payment-success-banner">
    <div class="check">✅</div>
    <h3>Paiement validé !</h3>
    <p>Uploade ta photo ci-dessous — ton Roast arrive dans les secondes qui suivent.</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 9 — UPLOAD IMAGE
# ══════════════════════════════════════════════════════════════════════════════

uploaded_file = st.file_uploader(
    "📸  Uploade ton meilleur (ou pire) flow",
    type=["png", "jpg", "jpeg"],
    label_visibility="visible",
)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 10 — LOGIQUE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

if uploaded_file is not None:

    # ── 10a. Aperçu + choix du mode ───────────────────────────────────────────
    st.markdown('<div class="result-card">', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="medium")

    with col1:
        image = Image.open(uploaded_file)
        st.image(image, caption="C'est ça ta tenue ?", use_container_width=True)

    with col2:
        st.markdown('<span class="mode-label">Choisis la violence :</span>', unsafe_allow_html=True)
        mode = st.radio(
            label="Mode d'analyse",
            options=[
                "💧 Drip Check — Gratuit",
                "😈 Roast Vestimentaire — 1,50 €",
            ],
            index=1 if st.session_state.a_paye else 0,
            label_visibility="collapsed",
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # ── 10b. Sélecteur de situation (contexte utilisateur) ────────────────────
    st.markdown('<span class="section-label">📍 Où tu vas avec ça ?</span>', unsafe_allow_html=True)

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
        # Fallback pour les versions de Streamlit sans st.pills
        pill_choix = st.selectbox(
            label="Situation",
            options=SITUATION_LABELS,
            label_visibility="collapsed",
        )
        situation_index = SITUATION_LABELS.index(pill_choix)

    situation_choisie = SITUATIONS[situation_index]
    situation_desc = situation_choisie["desc"]

    st.markdown("<br>", unsafe_allow_html=True)

    is_roast = "Roast" in mode

    # ── 10c. CTA dynamique selon mode et état paiement ────────────────────────
    lancer_analyse = False

    if not is_roast:
        if st.button("🚀  ANALYSER MON DRIP"):
            lancer_analyse = True
    else:
        if st.session_state.a_paye:
            if st.button("💀  LANCER MON ROAST"):
                lancer_analyse = True
        else:
            st.markdown(f"""
<div class="stripe-btn-wrapper">
    <a href="{STRIPE_LINK}" class="stripe-btn" target="_blank" rel="noopener noreferrer">
        💳&nbsp;&nbsp;PAYER 1,50 € ET SE FAIRE ROASTER
    </a>
    <p class="stripe-sub">Paiement sécurisé Stripe · Résultat immédiat après confirmation</p>
</div>
""", unsafe_allow_html=True)

    # ── 10d. Analyse IA ───────────────────────────────────────────────────────
    if lancer_analyse:

        with st.spinner("L'IA réfléchit à ta tenue... (c'est pas rapide, le jugement)"):

            # 1. Compression image (512x512 / qualité 60 → 85 tokens fixes)
            base64_image = compress_image_to_base64(image)

            # 2. Construction du prompt avec contexte injecté
            prompt = construire_prompt(is_roast, situation_desc)

            # 3. Appel API OpenAI
            try:
                reponse_brute = appeler_openai(base64_image, prompt)

                # 4. Extraction du CoT (<reflexion>) et nettoyage
                reflexion_text, reponse_propre = extraire_reflexion(reponse_brute)

                # 5. Parsing : nouveau format 7-8 champs
                r = parser_reponse(reponse_propre)

                # 6. Court-circuit si l'IA signale une erreur de visibilité
                if r["visibilite"].startswith("erreur"):
                    raison = r["visibilite"].replace("erreur:", "").strip()
                    message_ia = r["description"] or raison
                    titre_erreur = (
                        "📷 Photo illisible" if not is_roast
                        else "📷 Le Commissaire refuse de travailler dans le noir"
                    )
                    st.markdown(f"""
<div class="visibility-error">
    <div class="ve-icon">{"🔍" if not is_roast else "😤"}</div>
    <div class="ve-title">{titre_erreur}</div>
    <div class="ve-body">{message_ia}</div>
</div>
""", unsafe_allow_html=True)
                    # On affiche quand même le CoT si disponible
                    if reflexion_text:
                        with st.expander("🧠 Voir le raisonnement de l'IA"):
                            st.markdown(reflexion_text)

                else:
                    # Résultat normal — tenue bien visible

                    # 6. Consommation du crédit Roast (une seule utilisation)
                    if is_roast and st.session_state.a_paye:
                        st.session_state.a_paye = False

                    # 7. Badge de contexte
                    st.markdown(
                        f'<div class="context-badge">'
                        f'{situation_choisie["emoji"]} Analysé pour : {situation_choisie["label"]}'
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    # 8. Card "Description détaillée — preuve par l'image"
                    if r["description"]:
                        label_genre = r["genre"]
                        badge_html = (
                            f'<span class="genre-badge genre-{label_genre}">'
                            f'{"♂" if label_genre == "masculin" else "♀" if label_genre == "feminin" else "◈"}'
                            f" style {label_genre}</span>"
                        )
                        st.markdown(f"""
<div class="desc-card">
    <div class="desc-card-header">🔍 Ce que l'IA voit{badge_html}</div>
    <div class="desc-card-body">{r["description"]}</div>
</div>
""", unsafe_allow_html=True)

                    # 9. Score en grand
                    st.markdown(f"""
<div class="score-block">
    <div class="score-number">{r["score"]}</div>
    <div class="score-label">Style Score</div>
</div>
""", unsafe_allow_html=True)

                    # 10. Résultat principal (Drip ou Roast)
                    icone = "💡" if not is_roast else "☠️"
                    corps = f"**{r['titre']}**\n\n{r['analyse']}"
                    if r["conseil"]:
                        corps += f"\n\n{icone} *{r['conseil']}*"

                    if not is_roast:
                        st.success(corps)
                        st.balloons()
                    else:
                        st.error(corps)

                    # 11. Card affiliation (mode Drip uniquement, ID valide du catalogue)
                    if not is_roast and r["accessoire"] and r["accessoire"] in AFFILIATE_CATALOG:
                        prod = AFFILIATE_CATALOG[r["accessoire"]]
                        st.markdown(f"""
<a href="{prod['affiliate_url']}" target="_blank" rel="noopener noreferrer sponsored" class="affil-card">
    <div class="affil-emoji">{prod['emoji']}</div>
    <div class="affil-body">
        <div class="affil-header">✦ Le styliste recommande</div>
        <div class="affil-name">{prod['name']}</div>
        <div class="affil-tagline">{prod['tagline']}</div>
    </div>
    <div class="affil-cta">Voir →</div>
</a>
""", unsafe_allow_html=True)

                    # 12. Réflexion CoT dans un expander
                    if reflexion_text:
                        with st.expander("🧠 Voir le raisonnement de l'IA"):
                            st.markdown(reflexion_text)

            except Exception:
                st.error(
                    "Une erreur s'est produite lors de la connexion à l'IA. "
                    "Vérifie que ton compte OpenAI dispose bien de crédit."
                )


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 11 — FOOTER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="custom-footer">
    Fait avec 🔥 par <span>Juge Mon Style</span> · Powered by AI
</div>
""", unsafe_allow_html=True)