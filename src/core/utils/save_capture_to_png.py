from PIL import Image
import io
import base64

# Image base64 encodée (à remplacer par le contenu réel si besoin)
base64_img = '''iVBORw0KGgoAAAANSUhEUgAAAyAAAAJYCAYAAAB... (truncated)'''

# Décoder et sauvegarder l'image
img_bytes = base64.b64decode(base64_img)
img = Image.open(io.BytesIO(img_bytes))
img.save('/home/jpvw/Documents/node_appli/gemma_suite/doc/GEMMA-vide-capture.png')
print('Image sauvegardée dans doc/GEMMA-vide-capture.png')
