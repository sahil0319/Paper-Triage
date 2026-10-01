# SETUP_LOG
- git init: ok
- node v24.12.0, npm 11.6.2, python 3.12.12, git 2.55.0: ok
- uv: missing -> installed 0.12.21 via astral.sh script (~/.local/bin): ok
- spec-kit: first install attempt hung (slow PyPI index); retry with UV_HTTP_TIMEOUT=120 ok. `specify init --here --force --non-interactive --integration claude`: ok. .specify/ + speckit-* skills in .claude/skills: confirmed
- frontend-design: `npx skills add ... --skill frontend-design -y` ok (.agents/skills, symlinked into .claude/skills)
- impeccable: `npx impeccable install --project --providers=claude --no-hooks -y` ok (--no-hooks so it can't touch our hook config). Also added 4 impeccable-* agents to .claude/agents (tool default). `/impeccable init` is interactive -> PRODUCT.md written by hand
- caveman: `npx skills add JuliusBrussee/caveman -g -y` ok (global ~/.claude/skills + ~/.agents/skills; PromptScript target skipped, irrelevant)
- no-mistakes v1.84.0: installed to ~/.no-mistakes/bin, symlink ~/.local/bin. `no-mistakes init` DEFERRED: needs `origin` remote; will use local bare repo inside project (.local/origin.git, gitignored), never a real remote
- DESIGN.md: not present -> placeholder created
