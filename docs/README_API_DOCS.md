# API Reference Documentation Guide

This project supports auto-generating API documentation from Python docstrings using either **Sphinx** or **MkDocs**.

---

## 1. Using Sphinx

### a. Install Sphinx and Extensions
```bash
pip install sphinx sphinx-autodoc-typehints sphinx_rtd_theme
```

### b. Initialize Sphinx in the `docs/` Folder
```bash
cd docs
sphinx-quickstart
```
- Answer the prompts (project name, author, etc.).
- When asked, enable autodoc and type hints extensions.

### c. Configure Sphinx for Autodoc
- In `docs/conf.py`, add or ensure:
```python
import os
import sys
sys.path.insert(0, os.path.abspath('../src'))
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
]
html_theme = 'sphinx_rtd_theme'
```

### d. Add API Reference to `index.rst`
Add this to your `index.rst`:
```
.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api/modules
```

### e. Generate API Stubs
```bash
sphinx-apidoc -o api ../src
```

### f. Build the Docs
```bash
make html
```
- The HTML docs will be in `docs/_build/html/`.

---

## 2. Using MkDocs (with mkdocstrings)

### a. Install MkDocs and Plugins
```bash
pip install mkdocs mkdocstrings[python] mkdocs-material
```

### b. Create or Edit `mkdocs.yml`
Example minimal config:
```yaml
site_name: Crypto Trading Platform API
nav:
  - Home: index.md
  - API Reference: api.md
plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
```

### c. Create `docs/api.md`
Add:
```markdown
# API Reference

::: src.strats.base_strategy
::: src.trading.base_trading_bot
# (Add more modules/classes as needed)
```

### d. Build the Docs
```bash
mkdocs build
```
- The HTML docs will be in `site/`.

### e. Serve Locally
```bash
mkdocs serve
```
- Visit `http://127.0.0.1:8000/` in your browser.

---

## 3. Tips
- Keep your code docstrings up to date for best results.
- Regenerate docs after code changes.
- You can deploy the generated HTML to GitHub Pages or any static site host.

---

For more details, see the [Sphinx](https://www.sphinx-doc.org/) and [MkDocs](https://www.mkdocs.org/) documentation. 