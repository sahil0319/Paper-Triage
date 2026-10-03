"""T068: static checks of the DESIGN.md token layer, global type, focus, hover and motion in app.css.

Pure text parsing of `src/paper_triage/static/app.css`; runs offline, no browser.
"""

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[2] / "src" / "paper_triage" / "static"

COLORS = {
    "primary": "#0f62fe",
    "primary-hover": "#0050e6",
    "primary-active": "#002d9c",
    "on-primary": "#ffffff",
    "secondary": "#393939",
    "secondary-hover": "#474747",
    "secondary-active": "#6f6f6f",
    "link": "#0f62fe",
    "link-hover": "#0043ce",
    "link-active": "#002d9c",
    "ink": "#161616",
    "ink-muted": "#525252",
    "ink-subtle": "#6f6f6f",
    "ink-disabled": "#8c8c8c",
    "ink-inverse": "#ffffff",
    "canvas": "#ffffff",
    "surface-1": "#f4f4f4",
    "surface-2": "#e0e0e0",
    "surface-hover": "#e8e8e8",
    "surface-selected": "#e0e0e0",
    "surface-inverse": "#161616",
    "well": "#e0e0e0",
    "border-subtle": "#e0e0e0",
    "border-strong": "#8d8d8d",
    "border-page": "#c6c6c6",
    "focus": "#0f62fe",
    "focus-inset": "#ffffff",
    "error": "#da1e28",
    "error-hover": "#b81921",
    "error-active": "#750e13",
    "error-surface": "#fff1f1",
    "info": "#0f62fe",
    "info-surface": "#edf5ff",
    "selection": "#d0e2ff",
    "rank-track": "#e0e0e0",
    "rank-fill": "#161616",
    "cite-surface": "#e0e0e0",
    "cite-surface-active": "#c6c6c6",
}

HIGHLIGHTS = {"yellow": "#ffde66", "mint": "#9fe0c0", "peach": "#ffc29e"}

TYPES = {
    "heading-lg": "400 32px/40px var(--font-sans)",
    "heading-md": "400 24px/32px var(--font-sans)",
    "heading-sm": "400 20px/28px var(--font-sans)",
    "heading-xs": "600 16px/24px var(--font-sans)",
    "prose": "400 16px/24px var(--font-sans)",
    "body": "400 14px/20px var(--font-sans)",
    "body-compact": "400 14px/18px var(--font-sans)",
    "body-emphasis": "600 14px/18px var(--font-sans)",
    "label": "400 12px/16px var(--font-sans)",
    "mono": "400 12px/16px var(--font-mono)",
    "numeral-lg": "400 32px/40px var(--font-sans)",
    "numeral-md": "400 24px/32px var(--font-sans)",
}

SPACE = {
    "xxs": "4px",
    "xs": "8px",
    "sm": "12px",
    "md": "16px",
    "lg": "24px",
    "xl": "32px",
    "xxl": "48px",
}
RADIUS = {"none": "0", "xs": "2px", "pill": "9999px", "round": "50%"}
CONTROLS = {"sm": "32px", "md": "40px", "lg": "48px"}
MOTION = {
    "dur-fast": "110ms",
    "dur-moderate": "240ms",
    "dur-flash": "1600ms",
    "ease-standard": "cubic-bezier(0.2, 0, 0.38, 0.9)",
    "ease-entrance": "cubic-bezier(0, 0, 0.38, 0.9)",
    "ease-exit": "cubic-bezier(0.2, 0, 1, 0.9)",
}
LAYOUT = {
    "nav-h": "48px",
    "rail-w": "240px",
    "panel-w": "384px",
    "page-max": "1312px",
    "measure": "72ch",
}

OLD_TOKENS = [
    "--color-body",
    "--color-muted",
    "--color-hairline",
    "--color-edge-input",
    "--color-surface-soft",
    "--color-surface-strong",
    "--color-coral",
    "--color-cream",
    "--color-info-border",
    "--color-yellow",
    "--color-mint",
    "--color-peach",
    "--type-title-sm",
    "--type-reason",
    "--type-caption",
    "--type-chip",
    "--type-body-md",
    "--type-display-md",
]

# Custom properties set at runtime by app.js or pdf.js, not in CSS.
RUNTIME_PROPS = {"--rank", "--i", "--total-scale-factor", "--font-height", "--scale-x", "--rotate"}


def _css():
    return (STATIC / "app.css").read_text(encoding="utf-8")


def _strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _root_decls():
    css = _strip_comments(_css())
    decls = {}
    for block in re.findall(r":root\s*\{([^}]*)\}", css):
        for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", block):
            decls.setdefault(name, " ".join(value.split()))
    return decls


def _rules():
    """Yield (at-rule stack, selector prelude, body) for every style rule, nested at-rules included."""
    css = _strip_comments(_css())
    out = []
    stack = []  # prelude per open brace
    i = 0
    start = 0
    while i < len(css):
        c = css[i]
        if c == "{":
            stack.append(css[start:i].strip())
            start = i + 1
        elif c == "}":
            prelude = stack.pop() if stack else ""
            body = css[start:i]
            if not prelude.startswith("@") and "{" not in body:
                out.append((tuple(s for s in stack if s.startswith("@")), prelude, body))
            start = i + 1
        elif c == ";" and not stack:
            start = i + 1
        i += 1
    return out


def test_root_declares_color_tokens_with_exact_values():
    decls = _root_decls()
    for name, value in COLORS.items():
        assert decls.get(f"--color-{name}") == value, name
    for name, value in HIGHLIGHTS.items():
        assert decls.get(f"--hl-{name}") == value, name
    assert decls.get("--shadow-overlay") == "0 2px 6px rgba(0, 0, 0, 0.3)"
    assert decls.get("--color-overlay") == "rgba(22, 22, 22, 0.5)"


def test_root_declares_type_roles_and_font_stacks():
    decls = _root_decls()
    for role, value in TYPES.items():
        assert decls.get(f"--type-{role}") == value, role
    assert decls["--font-sans"].startswith('"IBM Plex Sans", "IBM Plex Sans Fallback"')
    assert decls["--font-mono"].startswith('"IBM Plex Mono"')
    assert decls.get("--tracking-prose") == "0.16px"
    assert decls.get("--tracking-label") == "0.32px"


def test_root_declares_space_radius_control_motion_and_layout():
    decls = _root_decls()
    for name, value in SPACE.items():
        assert decls.get(f"--space-{name}") == value, name
    for name, value in RADIUS.items():
        assert decls.get(f"--radius-{name}") == value, name
    for name, value in CONTROLS.items():
        assert decls.get(f"--control-{name}") == value, name
    for name, value in MOTION.items():
        assert decls.get(f"--{name}") == value, name
    for name, value in LAYOUT.items():
        assert decls.get(f"--{name}") == value, name
    assert "--pad-x" in decls


def test_old_tokens_are_gone():
    css = _css()
    for token in OLD_TOKENS:
        assert not re.search(re.escape(token) + r"(?![\w-])", css), token
    for token in (
        "--radius-sm",
        "--radius-md",
        "--radius-lg",
        "--radius-full",
        "--shadow-button",
        "--ring-focus",
        "--ease-out",
        "--dur-base",
        "--chat-w",
    ):
        assert not re.search(re.escape(token) + r"(?![\w-])", css), token
    assert "Airtable" not in css


def test_header_comment_names_carbon_and_design_md():
    first = _css().lstrip().split("*/", 1)[0]
    assert "Carbon-based, see DESIGN.md" in first


def test_every_var_used_is_declared():
    css = _strip_comments(_css())
    declared = set(re.findall(r"(--[\w-]+)\s*:", css))
    used = set(re.findall(r"var\(\s*(--[\w-]+)", css))
    missing = sorted(used - declared - RUNTIME_PROPS)
    assert not missing, missing


def test_no_literal_hex_outside_root():
    css = _strip_comments(_css())
    outside = re.sub(r":root\s*\{[^}]*\}", "", css)
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", outside)


def test_color_scheme_light_and_global_type():
    css = _strip_comments(_css())
    root = " ".join(re.findall(r":root\s*\{([^}]*)\}", css))
    assert re.search(r"color-scheme:\s*light", root)
    html_rule = next(b for _, p, b in _rules() if p == "html")
    assert re.search(r"font-synthesis:\s*none", html_rule)
    body_rule = next(b for _, p, b in _rules() if p == "body")
    assert re.search(r"font-variant-numeric:\s*tabular-nums", body_rule)
    assert re.search(r"font:\s*var\(--type-body\)", body_rule)


def test_every_hover_rule_is_inside_hover_media():
    hover = [(stack, prelude) for stack, prelude, _ in _rules() if ":hover" in prelude]
    for stack, prelude in hover:
        assert any("(hover: hover)" in s for s in stack), prelude
    # The hover tokens are actually used somewhere (the query is not just a stub).
    assert hover


def test_focus_system():
    rules = _rules()
    base = next(b for _, p, b in rules if p == ":focus-visible")
    assert "outline: 2px solid var(--color-focus)" in base
    assert "outline-offset: 2px" in base
    css = _strip_comments(_css())
    # Filled buttons: inset ring, plus the white inner ring.
    assert "box-shadow: inset 0 0 0 3px var(--color-focus-inset)" in css
    assert "outline-offset: -2px" in css
    # tabindex="-1" targets show no ring.
    assert any(
        'tabindex="-1"' in p and ":focus-visible" in p and "outline: none" in b for _, p, b in rules
    )


def test_motion_uses_tokens_not_literals():
    css = _strip_comments(_css())
    outside = re.sub(r":root\s*\{[^}]*\}", "", css)
    # Durations come from tokens; only the working loops are literal (1.2s rays with a 150ms stagger,
    # 2.4s breathe).
    literals = re.findall(r"(?<![\w.-])\d*\.?\d+m?s\b", outside)
    assert set(literals) <= {"1.2s", "2.4s", "150ms"}, literals


def test_reduced_motion_and_forced_colors_blocks_remain():
    css = _css()
    assert "@keyframes ray" in css and "@keyframes breathe" in css
    assert "prefers-reduced-motion: reduce" in css
    assert "forced-colors: active" in css
    reduced = next(s for s, _, _ in _rules() if any("prefers-reduced-motion" in x for x in s))
    assert reduced
