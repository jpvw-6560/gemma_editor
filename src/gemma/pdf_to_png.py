from pdf2image import convert_from_path

pdf_path = "/home/jpvw/Documents/node_appli/gemma_suite/doc/GEMMA-vide.pdf"
out_path = "/home/jpvw/Documents/node_appli/gemma_suite/doc/GEMMA-vide.png"

# Convertir la première page du PDF en image PNG
images = convert_from_path(pdf_path, dpi=150)
images[0].save(out_path, 'PNG')
print(f"Image enregistrée : {out_path}")
