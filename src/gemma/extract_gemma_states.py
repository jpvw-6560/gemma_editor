import fitz

pdf_path = "/home/jpvw/Documents/node_appli/gemma_suite/doc/GEMMA-vide.pdf"
doc = fitz.open(pdf_path)

for page_num in range(len(doc)):
    page = doc[page_num]
    blocks = page.get_text("blocks")
    print(f"Page {page_num+1}")
    for b in blocks:
        x0, y0, x1, y1, text, *_ = b
        if text.strip():
            print(f"({x0:.0f}, {y0:.0f}, {x1-x0:.0f}, {y1-y0:.0f}): {text.strip()}")
