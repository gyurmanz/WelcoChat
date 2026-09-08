#!/usr/bin/env python3
"""Builds the multi-language public site into ../site from site-src/locales + templates.

Usage: python3 build_site.py

For each supported language, renders home/terms/privacy/guide pages by merging that
language's locale JSON over the English canonical content (missing keys fall back to
English, so a partially-translated language still renders a complete page). Also writes
a root redirector, robots.txt, sitemap.xml (with hreflang alternates), and thin redirect
stubs at the old un-prefixed URLs.
"""
import json
import os
import shutil

SITE_SRC = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SITE_SRC)
OUT = os.path.join(ROOT, "site")
LOCALES_DIR = os.path.join(SITE_SRC, "locales")
TEMPLATES_DIR = os.path.join(SITE_SRC, "templates")
BASE_URL = "https://welcochat.com"

LANGUAGES = [
    ("en", "English"),
    ("de", "Deutsch"),
    ("fr", "Français"),
    ("hu", "Magyar"),
    ("pl", "Polski"),
    ("sk", "Slovenčina"),
    ("hr", "Hrvatski"),
    ("el", "Ελληνικά"),
    ("es", "Español"),
]
DEFAULT_LANG = "en"

PAGES = [
    # (page_key, url_path, changefreq, priority)
    ("home", "", "weekly", "1.0"),
    ("terms", "terms/", "monthly", "0.3"),
    ("privacy", "privacy/", "monthly", "0.3"),
    ("guidePromptContent", "guides/prompt-and-content-guide/", "monthly", "0.5"),
    ("guideSlackTeams", "guides/slack-teams-setup/", "monthly", "0.5"),
]


def deep_merge(base, override):
    """Merge override onto base. Dicts recurse; lists/scalars in override replace base entirely."""
    if isinstance(base, dict) and isinstance(override, dict):
        result = dict(base)
        for k, v in override.items():
            if k in result:
                result[k] = deep_merge(result[k], v)
            else:
                result[k] = v
        return result
    return override if override is not None else base


def load_locale(lang):
    en = json.load(open(os.path.join(LOCALES_DIR, "en.json"), encoding="utf-8"))
    if lang == "en":
        return en
    path = os.path.join(LOCALES_DIR, f"{lang}.json")
    if not os.path.exists(path):
        return en
    override = json.load(open(path, encoding="utf-8"))
    return deep_merge(en, override)


def read_template(name):
    with open(os.path.join(TEMPLATES_DIR, name), encoding="utf-8") as f:
        return f.read()


def fill(template, values):
    out = template
    for key, val in values.items():
        out = out.replace("{{" + key + "}}", val)
    return out


def url_for(lang, path):
    return f"{BASE_URL}/{lang}/{path}"


def hreflang_links(path):
    lines = []
    for code, _ in LANGUAGES:
        lines.append(f'  <link rel="alternate" hreflang="{code}" href="{url_for(code, path)}" />')
    lines.append(f'  <link rel="alternate" hreflang="x-default" href="{url_for(DEFAULT_LANG, path)}" />')
    return "\n".join(lines)


CHECK_ICON = ('<svg class="lang-switch-check" width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
              '<path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def lang_switcher_options(current_lang, path):
    lines = []
    for code, name in LANGUAGES:
        is_current = code == current_lang
        li_class = ' class="is-current"' if is_current else ""
        aria_selected = "true" if is_current else "false"
        check = CHECK_ICON if is_current else ""
        lines.append(
            f'            <li{li_class} role="option" aria-selected="{aria_selected}">'
            f'<a href="{url_for(code, path)}">{name}{check}</a></li>'
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Page content renderers — each returns the inner <main> HTML for that page.
# ---------------------------------------------------------------------------

def check_svg():
    return ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none">'
            '<path d="M5 13l4 4L19 7" stroke="#004a9c" stroke-width="2.4" '
            'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def x_svg():
    return ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none">'
            '<path d="M6 6L18 18M18 6L6 18" stroke="#f68c36" stroke-width="2" '
            'stroke-linecap="round"/></svg>')


def chevron_svg():
    return ('<svg class="chev" width="16" height="16" viewBox="0 0 24 24" fill="none">'
            '<path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round"/></svg>')


FEATURE_ICONS = [
    '<path d="M4 6h16M4 12h16M4 18h10" stroke="#004a9c" stroke-width="2" stroke-linecap="round"/>',
    '<rect x="4" y="5" width="16" height="12" rx="2" stroke="#004a9c" stroke-width="2"/><path d="M9 21h6" stroke="#004a9c" stroke-width="2" stroke-linecap="round"/>',
    '<path d="M12 12a4 4 0 100-8 4 4 0 000 8zM4 20c0-4 3.5-6 8-6s8 2 8 6" stroke="#004a9c" stroke-width="2" stroke-linecap="round"/>',
    '<path d="M8 10h8M8 14h5" stroke="#004a9c" stroke-width="2" stroke-linecap="round"/><path d="M4 6h16v10H9l-5 4V6z" stroke="#004a9c" stroke-width="2" stroke-linejoin="round"/>',
    '<path d="M4 19V9m6 10V5m6 14v-7" stroke="#004a9c" stroke-width="2" stroke-linecap="round"/>',
    '<path d="M13 3L4 14h7l-1 7 9-11h-7l1-7z" stroke="#004a9c" stroke-width="2" stroke-linejoin="round"/>',
    '<path d="M12 3a9 9 0 100 18 9 9 0 000-18zM8 12l3 3 5-6" stroke="#004a9c" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    '<circle cx="9" cy="8" r="3" stroke="#004a9c" stroke-width="2"/><path d="M3 20c0-3 2.5-5 6-5s6 2 6 5" stroke="#004a9c" stroke-width="2" stroke-linecap="round"/><circle cx="17" cy="8" r="2.4" stroke="#004a9c" stroke-width="2"/><path d="M15.5 15.2c2.7.3 4.5 2 4.5 4.8" stroke="#004a9c" stroke-width="2" stroke-linecap="round"/>',
    '<path d="M4 12l6-8 10 4-2 10-8 2-6-8z" stroke="#004a9c" stroke-width="2" stroke-linejoin="round"/>',
    '<path d="M16 18l4-6-4-6M8 6l-4 6 4 6" stroke="#004a9c" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    '<rect x="4" y="4" width="16" height="16" rx="2" stroke="#004a9c" stroke-width="2"/><path d="M4 15l4-4 3 3 5-5 4 4" stroke="#004a9c" stroke-width="2" stroke-linejoin="round"/>',
    '<path d="M4 12h16M12 4c2.5 2.5 4 5.5 4 8s-1.5 5.5-4 8c-2.5-2.5-4-5.5-4-8s1.5-5.5 4-8z" stroke="#004a9c" stroke-width="2"/>',
]


def render_home_content(t, lang, section_prefix, terms_href, privacy_href):
    home = t["home"]
    v = home["heroVisual"]
    output_cards = "".join(
        f'      <div class="output-card"><b>{c["title"]}</b>{c["body"]}</div>\n'
        for c in home["outputCards"]
    )
    pain_items = "".join(
        f'        <div class="pain-item">\n          {x_svg()}\n          <span>{item}</span>\n        </div>\n'
        for item in home["painItems"]
    )
    steps = "".join(
        f'        <div class="step"><div class="step-num">{i + 1}</div><h3>{s["title"]}</h3><p>{s["body"]}</p></div>\n'
        for i, s in enumerate(home["howItWorks"]["steps"])
    )
    feature_cards = ""
    for i, c in enumerate(home["features"]["cards"]):
        icon = FEATURE_ICONS[i % len(FEATURE_ICONS)]
        tier_html = f'\n          <span class="feature-tier">{c["tier"]}</span>' if c.get("tier") else ""
        feature_cards += (
            f'        <div class="feature-card">\n'
            f'          <div class="feature-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none">{icon}</svg></div>\n'
            f'          <h3>{c["title"]}</h3>\n'
            f'          <p>{c["body"]}</p>{tier_html}\n'
            f'        </div>\n'
        )
    pricing = home["pricing"]
    price_cards = ""
    for tier in pricing["tiers"]:
        badge = f'          <span class="price-badge">{pricing["recommended"]}</span>\n' if tier.get("recommended") else ""
        card_class = "price-card recommended" if tier.get("recommended") else "price-card"
        btn_class = "btn btn-primary" if tier.get("recommended") else "btn btn-outline"
        features_html = "".join(
            f'            <li>{check_svg()} {feat}</li>\n' for feat in tier["features"]
        )
        price_cards += (
            f'        <div class="{card_class}">\n'
            f'{badge}'
            f'          <div class="price-tier">{tier["name"]}</div>\n'
            f'          <div class="price-amount"><span class="m-price">{tier["priceMonthly"]}</span>'
            f'<span class="a-price">{tier["priceAnnual"]}</span><span>{pricing["perMo"]}</span></div>\n'
            f'          <div class="price-annual-note">{pricing["billedAnnually"]}</div>\n'
            f'          <ul class="price-features">\n{features_html}          </ul>\n'
            f'          <a href="/portal/signup" class="{btn_class}">{pricing["startFreeTrial"]}</a>\n'
            f'        </div>\n'
        )
    faq_items = ""
    faq_ld = []
    for item in home["faq"]["items"]:
        faq_items += (
            f'        <div class="faq-item"><button class="faq-q">{item["q"]} {chevron_svg()}</button>'
            f'<div class="faq-a"><p>{item["a"]}</p></div></div>\n'
        )
        faq_ld.append({"@type": "Question", "name": item["q"], "acceptedAnswer": {"@type": "Answer", "text": item["a"]}})
    contact = home["contact"]
    topic_options = "".join(
        f'            <option value="{o["value"]}">{o["label"]}</option>\n' for o in contact["form"]["topics"]
    )

    ld_app = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "WelcoChat",
        "url": url_for(lang, ""),
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web",
        "description": t["meta"]["home"]["description"],
        "offers": {"@type": "AggregateOffer", "priceCurrency": "EUR", "lowPrice": "39", "highPrice": "299", "offerCount": "3"},
        "provider": {"@type": "Organization", "name": "WelcoChat", "url": url_for(lang, "")},
    }
    ld_faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_ld}

    return f"""  <!-- HERO -->
  <section class="hero">
    <div class="container hero-grid">
      <div>
        <div class="eyebrow"><span class="eyebrow-dot"></span> {home["eyebrow"]}</div>
        <h1>{home["h1"]}</h1>
        <p class="hero-sub">{home["heroSub"]}</p>
        <div class="hero-actions">
          <a href="/portal/signup" class="btn btn-primary btn-lg">{t["common"]["createAccount"]}</a>
          <a href="{section_prefix}#contact" class="btn btn-outline btn-lg">{home["contactUs"]}</a>
        </div>
        <p class="hero-note">{home["heroNote"]}</p>
      </div>

      <div class="hero-visual">
        <div class="hero-visual-head">
          <svg width="18" height="18" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="6" y="6" width="52" height="40" rx="16" fill="white" fill-opacity="0.18"/>
            <path d="M21 27 L29 35 L44 18" stroke="#F68C36" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          </svg>
          {t["common"]["brand"]}
        </div>
        <div class="hero-chat">
          <div class="bubble visitor">{v["bubbleVisitor1"]}</div>
          <div class="bubble agent">{v["bubbleAgent1"]}</div>
          <div class="bubble visitor">{v["bubbleVisitor2"]}</div>
          <div class="bubble handoff"><span class="dot"></span> {v["bubbleHandoff"]}</div>
        </div>
      </div>
    </div>

    <div class="container output-cards">
{output_cards}    </div>
  </section>

  <!-- PROBLEM -->
  <section class="tight">
    <div class="container">
      <h2>{home["problem"]["h2"]}</h2>
      <p class="problem-body">{home["problem"]["body"]}</p>

      <div class="pain-grid">
{pain_items}      </div>
    </div>
  </section>

  <!-- HOW IT WORKS -->
  <section id="how-it-works">
    <div class="container">
      <h2>{home["howItWorks"]["h2"]}</h2>
      <div class="steps">
{steps}      </div>
    </div>
  </section>

  <!-- FEATURES -->
  <section id="features" class="tight">
    <div class="container">
      <h2>{home["features"]["h2"]}</h2>
      <div class="feature-grid">
{feature_cards}      </div>
    </div>
  </section>

  <!-- PRICING -->
  <section id="pricing">
    <div class="container">
      <h2>{pricing["h2"]}</h2>
      <p class="pricing-note">{pricing["note"]}</p>

      <div class="billing-toggle" role="group" aria-label="Billing period">
        <button class="billing-opt active" data-billing="monthly">{pricing["monthly"]}</button>
        <button class="billing-opt" data-billing="annual">{pricing["annual"]} <span class="save-badge">{pricing["save20"]}</span></button>
      </div>

      <div class="pricing-grid" id="pricingGrid">
{price_cards}      </div>

      <p class="pricing-foot">{pricing["foot"]}</p>
    </div>
  </section>

  <!-- FAQ -->
  <section id="faq" class="tight">
    <div class="container">
      <h2 style="text-align:center;">{home["faq"]["h2"]}</h2>
      <div class="faq-list">
{faq_items}      </div>
    </div>
  </section>

  <!-- CONTACT -->
  <section id="contact">
    <div class="container contact-grid">
      <div>
        <h2>{contact["h2"]}</h2>
        <p class="hero-sub">{contact["sub"]}</p>
        <div class="contact-info">
          <div class="contact-info-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M4 6h16v12H4z" stroke="#004a9c" stroke-width="2"/><path d="M4 7l8 6 8-6" stroke="#004a9c" stroke-width="2"/></svg>
            <div><b>{contact["emailLabel"]}</b><span>{contact["email"]}</span></div>
          </div>
          <div class="contact-info-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 21s7-6.5 7-12a7 7 0 10-14 0c0 5.5 7 12 7 12z" stroke="#004a9c" stroke-width="2"/><circle cx="12" cy="9" r="2.4" stroke="#004a9c" stroke-width="2"/></svg>
            <div><b>{contact["responseLabel"]}</b><span>{contact["response"]}</span></div>
          </div>
        </div>
      </div>

      <form class="contact-form" id="contactForm">
        <div class="form-row">
          <label for="name">{contact["form"]["name"]}</label>
          <input id="name" name="name" type="text" required />
        </div>
        <div class="form-row">
          <label for="company">{contact["form"]["company"]}</label>
          <input id="company" name="company" type="text" />
        </div>
        <div class="form-row">
          <label for="email">{contact["form"]["email"]}</label>
          <input id="email" name="email" type="email" required />
        </div>
        <div class="form-row">
          <label for="website">{contact["form"]["website"]}</label>
          <input id="website" name="website" type="text" placeholder="https://" />
        </div>
        <div class="form-row">
          <label for="topic">{contact["form"]["topicLabel"]}</label>
          <select id="topic" name="topic">
{topic_options}          </select>
        </div>
        <div class="form-row">
          <label for="message">{contact["form"]["message"]}</label>
          <textarea id="message" name="message" rows="4" required></textarea>
        </div>
        <button type="submit" class="btn btn-primary" id="contactSubmit" data-sending-label="{contact["form"]["sending"]}" data-success-label="{contact["form"]["success"]}" data-error-label="{contact["form"]["errorGeneric"]}">{contact["form"]["submit"]}</button>
        <p class="form-msg" id="formMsg"></p>
      </form>
    </div>
  </section>
""", ld_app, ld_faq


def render_legal_section_list(bullets):
    items = "".join(f'        <li><strong>{b["strong"]}</strong>{b["text"]}</li>\n' for b in bullets)
    return f'      <ul>\n{items}      </ul>\n'


def render_terms_content(t, lang, privacy_href):
    terms = t["terms"]
    sections_html = ""
    for s in terms["sections"]:
        body = s["body"].replace("{{PRIVACY_URL}}", privacy_href)
        sections_html += f'      <h2>{s["h2"]}</h2>\n      <p>{body}</p>\n\n'
    return f"""    <div class="container legal-content">
      <div class="eyebrow"><span class="eyebrow-dot"></span> {terms["eyebrow"]}</div>
      <h1 style="font-size:clamp(1.8rem,3vw,2.6rem);">{terms["h1"]}</h1>
      <p class="legal-updated">{t["common"]["legalUpdated"]}</p>

      <p>{terms["intro"]}</p>

      <p class="legal-note">{terms["note"]}</p>

{sections_html}    </div>
"""


def render_privacy_content(t, lang):
    privacy = t["privacy"]
    data_items = "".join(f'        <li><strong>{i["strong"]}</strong>{i["text"]}</li>\n' for i in privacy["dataWeCollectItems"])
    share_items = "".join(f'        <li><strong>{i["strong"]}</strong>{i["text"]}</li>\n' for i in privacy["whoWeShareItems"])
    sections_html = ""
    for s in privacy["sections"]:
        sections_html += f'      <h2>{s["h2"]}</h2>\n      <p>{s["body"]}</p>\n\n'
    return f"""    <div class="container legal-content">
      <div class="eyebrow"><span class="eyebrow-dot"></span> {privacy["eyebrow"]}</div>
      <h1 style="font-size:clamp(1.8rem,3vw,2.6rem);">{privacy["h1"]}</h1>
      <p class="legal-updated">{t["common"]["legalUpdated"]}</p>

      <p>{privacy["intro"]}</p>

      <p class="legal-note">{privacy["note"]}</p>

      <h2>1. Data we collect</h2>
      <p>{privacy["dataWeCollectIntro"]}</p>
      <ul>
{data_items}      </ul>

      <h2>4. Who we share data with</h2>
      <p>{privacy["whoWeShareIntro"]}</p>
      <ul>
{share_items}      </ul>
      <p>{privacy["whoWeShareFoot"]}</p>

{sections_html}    </div>
"""


def render_guide_prompt_content(t, lang):
    g = t["guidePromptContent"]
    sections_html = ""
    for s in g["sections"]:
        sections_html += f'      <h2>{s["h2"]}</h2>\n'
        if "body" in s:
            sections_html += f'      <p>{s["body"]}</p>\n'
        if "list" in s:
            items = "".join(f'        <li>{item}</li>\n' for item in s["list"])
            sections_html += f'      <ul>\n{items}      </ul>\n'
        if "list_strong" in s:
            sections_html += render_legal_section_list(s["list_strong"])
        if "after" in s:
            sections_html += f'      <p>{s["after"]}</p>\n'
        sections_html += "\n"
    return f"""    <div class="container legal-content">
      <div class="eyebrow"><span class="eyebrow-dot"></span> {g["eyebrow"]}</div>
      <h1 style="font-size:clamp(1.8rem,3vw,2.6rem);">{g["h1"]}</h1>
      <p class="legal-updated">{g["sub"]}</p>

      <p>{g["intro"]}</p>

{sections_html}      <p style="margin-top:2.5rem;"><a href="/portal">{t["common"]["backToPortal"]}</a></p>
    </div>
"""


def render_guide_slack_teams(t, lang):
    g = t["guideSlackTeams"]
    slack_steps = "".join(f'        <li>{s}</li>\n' for s in g["slack"]["steps"])
    teams_steps = "".join(f'        <li>{s}</li>\n' for s in g["teams"]["steps"])
    return f"""    <div class="container legal-content">
      <div class="eyebrow"><span class="eyebrow-dot"></span> {g["eyebrow"]}</div>
      <h1 style="font-size:clamp(1.8rem,3vw,2.6rem);">{g["h1"]}</h1>
      <p class="legal-updated">{g["sub"]}</p>

      <p>{g["intro"]}</p>

      <h2>{g["slack"]["h2"]}</h2>
      <ol>
{slack_steps}      </ol>

      <h2>{g["teams"]["h2"]}</h2>
      <p>{g["teams"]["intro"]}</p>
      <ol>
{teams_steps}      </ol>
      <p class="legal-note">{g["teams"]["note"]}</p>

      <h2>{g["generic"]["h2"]}</h2>
      <p>{g["generic"]["body"]}</p>

      <h2>{g["testing"]["h2"]}</h2>
      <p>{g["testing"]["body"]}</p>

      <p style="margin-top:2.5rem;"><a href="/portal">{t["common"]["backToPortal"]}</a></p>
    </div>
"""


def render_page(page_key, lang, t):
    path = dict((p[0], p[1]) for p in PAGES)[page_key]
    section_prefix = "" if page_key == "home" else f"/{lang}/"
    home_href = f"/{lang}/"
    terms_href = f"/{lang}/terms/"
    privacy_href = f"/{lang}/privacy/"

    ld_app = ld_faq = None
    if page_key == "home":
        content, ld_app, ld_faq = render_home_content(t, lang, section_prefix, terms_href, privacy_href)
    elif page_key == "terms":
        content = render_terms_content(t, lang, privacy_href)
    elif page_key == "privacy":
        content = render_privacy_content(t, lang)
    elif page_key == "guidePromptContent":
        content = render_guide_prompt_content(t, lang)
    elif page_key == "guideSlackTeams":
        content = render_guide_slack_teams(t, lang)
    else:
        raise ValueError(page_key)

    extra_head = ""
    og_type = "article" if page_key.startswith("guide") else "website"
    if page_key == "home":
        extra_head = (
            f'  <script type="application/ld+json">\n{json.dumps(ld_app, indent=2, ensure_ascii=False)}\n  </script>\n'
            f'  <script type="application/ld+json">\n{json.dumps(ld_faq, indent=2, ensure_ascii=False)}\n  </script>\n'
        )

    meta = t["meta"][page_key]
    base = read_template("base.html")
    values = {
        "LANG": lang,
        "TITLE": meta["title"],
        "DESCRIPTION": meta["description"],
        "OG_TITLE": meta["ogTitle"],
        "OG_DESCRIPTION": meta["ogDescription"],
        "OG_TYPE": og_type,
        "CANONICAL_URL": url_for(lang, path),
        "HREFLANG_LINKS": hreflang_links(path),
        "EXTRA_HEAD": extra_head,
        "HOME_HREF": home_href,
        "LANG_CODE_UPPER": lang.upper(),
        "BRAND": t["common"]["brand"],
        "SECTION_PREFIX": section_prefix,
        "NAV_FEATURES": t["common"]["nav"]["features"],
        "NAV_HOW": t["common"]["nav"]["howItWorks"],
        "NAV_PRICING": t["common"]["nav"]["pricing"],
        "NAV_FAQ": t["common"]["nav"]["faq"],
        "NAV_CONTACT": t["common"]["nav"]["contact"],
        "LANG_SWITCH_LABEL": t["common"]["langSwitchLabel"],
        "LANG_SWITCHER_OPTIONS": lang_switcher_options(lang, path),
        "SIGN_IN": t["common"]["signIn"],
        "CREATE_ACCOUNT": t["common"]["createAccount"],
        "TOGGLE_MENU": t["common"]["toggleMenu"],
        "CONTENT": content,
        "FOOTER_TAGLINE": t["common"]["footer"]["tagline"],
        "FOOTER_PRODUCT_HEADING": t["common"]["footer"]["productHeading"],
        "FOOTER_COMPANY_HEADING": t["common"]["footer"]["companyHeading"],
        "FOOTER_PORTAL": t["common"]["footer"]["portal"],
        "FOOTER_TERMS": t["common"]["footer"]["terms"],
        "FOOTER_PRIVACY": t["common"]["footer"]["privacy"],
        "TERMS_HREF": terms_href,
        "PRIVACY_HREF": privacy_href,
        "FOOTER_COPYRIGHT": t["common"]["footer"]["copyright"],
    }
    return fill(base, values)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

REDIRECT_STUB = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta http-equiv="refresh" content="0; url={target}" />
<link rel="canonical" href="{target}" />
<script>location.replace("{target}");</script>
</head>
<body>
<p>This page has moved to <a href="{target}">{target}</a>.</p>
</body>
</html>
"""

ROOT_REDIRECTOR = """<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>WelcoChat</title>
<meta http-equiv="refresh" content="0; url=/en/" />
<link rel="canonical" href="https://welcochat.com/en/" />
<script>
(function () {{
  var SUPPORTED = {supported};
  var STORAGE_KEY = 'welco_lang';
  var lang = null;
  try {{ lang = localStorage.getItem(STORAGE_KEY); }} catch (e) {{}}
  if (!lang || SUPPORTED.indexOf(lang) === -1) {{
    var langs = navigator.languages || [navigator.language || 'en'];
    for (var i = 0; i < langs.length; i++) {{
      var code = (langs[i] || '').slice(0, 2).toLowerCase();
      if (SUPPORTED.indexOf(code) !== -1) {{ lang = code; break; }}
    }}
  }}
  if (!lang || SUPPORTED.indexOf(lang) === -1) lang = 'en';
  try {{ localStorage.setItem(STORAGE_KEY, lang); }} catch (e) {{}}
  location.replace('/' + lang + '/');
}})();
</script>
</head>
<body>
<p>Redirecting to <a href="/en/">welcochat.com/en/</a>&hellip;</p>
</body>
</html>
"""


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def build():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT, exist_ok=True)

    locales = {code: load_locale(code) for code, _ in LANGUAGES}

    for code, _ in LANGUAGES:
        t = locales[code]
        for page_key, path, _freq, _prio in PAGES:
            html = render_page(page_key, code, t)
            out_path = os.path.join(OUT, code, path, "index.html") if path else os.path.join(OUT, code, "index.html")
            write(out_path, html)

    # Shared static assets
    for name in ["styles.css", "app.js", "favicon.ico"]:
        src = os.path.join(ROOT, "site-static", name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(OUT, name))
    assets_src = os.path.join(ROOT, "site-static", "assets")
    if os.path.exists(assets_src):
        shutil.copytree(assets_src, os.path.join(OUT, "assets"))

    # Root redirector
    supported_json = json.dumps([c for c, _ in LANGUAGES])
    write(os.path.join(OUT, "index.html"), ROOT_REDIRECTOR.format(supported=supported_json))

    # Thin stubs at the old un-prefixed URLs -> English
    write(os.path.join(OUT, "terms", "index.html"), REDIRECT_STUB.format(target="/en/terms/"))
    write(os.path.join(OUT, "privacy", "index.html"), REDIRECT_STUB.format(target="/en/privacy/"))
    write(os.path.join(OUT, "guides", "prompt-and-content-guide", "index.html"),
          REDIRECT_STUB.format(target="/en/guides/prompt-and-content-guide/"))
    write(os.path.join(OUT, "guides", "slack-teams-setup", "index.html"),
          REDIRECT_STUB.format(target="/en/guides/slack-teams-setup/"))

    # robots.txt
    write(os.path.join(OUT, "robots.txt"),
          "User-agent: *\nAllow: /\nDisallow: /portal/\nDisallow: /api/\n\nSitemap: https://welcochat.com/sitemap.xml\n")

    # sitemap.xml with hreflang alternates
    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for page_key, path, freq, prio in PAGES:
        for code, _ in LANGUAGES:
            sitemap_lines.append("  <url>")
            sitemap_lines.append(f"    <loc>{url_for(code, path)}</loc>")
            for alt_code, _ in LANGUAGES:
                sitemap_lines.append(
                    f'    <xhtml:link rel="alternate" hreflang="{alt_code}" href="{url_for(alt_code, path)}" />'
                )
            sitemap_lines.append(
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="{url_for(DEFAULT_LANG, path)}" />'
            )
            sitemap_lines.append(f"    <changefreq>{freq}</changefreq>")
            sitemap_lines.append(f"    <priority>{prio}</priority>")
            sitemap_lines.append("  </url>")
    sitemap_lines.append("</urlset>")
    write(os.path.join(OUT, "sitemap.xml"), "\n".join(sitemap_lines) + "\n")

    print(f"Built {len(LANGUAGES)} languages x {len(PAGES)} pages into {OUT}")


if __name__ == "__main__":
    build()
