# PolyToken final deck

[PDF](PolyToken_deck.pdf) · [Editable PowerPoint](PolyToken_deck.pptx) · [Slide contact sheet](contact_sheet.png) · [Individual slide PNGs](slides/)

Ten 16:9 slides use the console’s dark semantic palette and Arial. Tables, diagrams and the comparison chart are editable PowerPoint objects. Source footers and slide notes point to the repository evidence; [evidence.json](evidence.json) includes report hashes, exact claim IDs and derived monthly costs.

Rebuild from the repository root:

```sh
.venv/bin/python scripts/video/prepare_evidence.py
node scripts/video/build-deck.cjs
soffice --headless --convert-to pdf --outdir docs/deck docs/deck/PolyToken_deck.pptx
pdftoppm -scale-to-x 1920 -scale-to-y 1080 -png docs/deck/PolyToken_deck.pdf docs/deck/slides/slide
```

Requires `pptxgenjs`, LibreOffice and Poppler as authoring tools; they are not application dependencies. Set `NODE_PATH` to an installed package directory if necessary. The final PDF and PNGs were rendered from the generated PPTX, and the PPTX passed schema, relationship and chart validation.

The company samples are fictional. Cost candidates are not voice deployment recommendations, and no cost estimate establishes quality.
