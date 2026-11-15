import os
import shutil
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_ORIGEN = os.path.join(BASE_DIR, "fotos_sin_ordenar")
CARPETA_DESTINO = os.path.join(BASE_DIR, "fotos_ordenadas")
CONFIANZA_MINIMA = 55.0

CATEGORIAS = {
    "hombre": "a photo of a man, male fashion, men's clothing, or male portrait",
    "mujer": "a photo of a woman, female fashion, women's clothing, or female portrait",
    "accesorios": "a photo of fashion accessories, jewelry, watches, handbags, sunglasses, hats, or shoes",
    "maquillaje": "a photo of makeup products, cosmetics, lipstick, eyeshadow, foundation, or beauty items"
}

if not os.path.exists(CARPETA_ORIGEN):
    print(f"❌ ERROR: No encuentro la carpeta '{CARPETA_ORIGEN}'")
    exit()

# Buscar imágenes (incluyendo subcarpetas y .jfif)
extensiones_validas = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".jfif", ".tiff", ".gif")
rutas_imagenes = []

for raiz, carpetas, archivos in os.walk(CARPETA_ORIGEN):
    for archivo in archivos:
        if archivo.lower().endswith(extensiones_validas):
            rutas_imagenes.append(os.path.join(raiz, archivo))

total = len(rutas_imagenes)
if total == 0:
    print(f"⚠️ Se encontraron 0 imágenes en: {CARPETA_ORIGEN}")
    exit()

# --- CARGAR MODELO ---
print(f"✅ Se encontraron {total} imágenes. Cargando modelo de IA...")
modelo_id = "openai/clip-vit-base-patch32"
modelo = CLIPModel.from_pretrained(modelo_id)
procesador = CLIPProcessor.from_pretrained(modelo_id)

nombres_carpetas = list(CATEGORIAS.keys())
descripciones = list(CATEGORIAS.values())

for categoria in nombres_carpetas + ["revisar"]:
    os.makedirs(os.path.join(CARPETA_DESTINO, categoria), exist_ok=True)

# --- PROCESAR IMÁGENES ---
for i, ruta_imagen in enumerate(rutas_imagenes, 1):
    nombre_archivo = os.path.basename(ruta_imagen)
    
    try:
        imagen = Image.open(ruta_imagen).convert("RGB")
        inputs = procesador(text=descripciones, images=imagen, return_tensors="pt", padding=True)
        
        with torch.no_grad():
            outputs = modelo(**inputs)
            # Convertir el resultado a una lista simple de Python
            lista_probs = outputs.logits_per_image.softmax(dim=1).squeeze().tolist()
        
        # Buscar el valor más alto en la lista
        max_prob = max(lista_probs)
        indice_ganador = lista_probs.index(max_prob)
        confianza = max_prob * 100
        
        if confianza >= CONFIANZA_MINIMA:
            carpeta_final = nombres_carpetas[indice_ganador]
        else:
            carpeta_final = "revisar"
            
        # Convertir .jfif a .jpg al guardar y evitar nombres repetidos
        nombre_base, ext = os.path.splitext(nombre_archivo)
        if ext.lower() == ".jfif":
            ext = ".jpg"

        ruta_destino = os.path.join(CARPETA_DESTINO, carpeta_final, f"{nombre_base}{ext}")
        if os.path.exists(ruta_destino):
            ruta_destino = os.path.join(CARPETA_DESTINO, carpeta_final, f"{nombre_base}_{i}{ext}")

        if nombre_archivo.lower().endswith(".jfif"):
            imagen.save(ruta_destino, "JPEG", quality=95)
        else:
            shutil.copy2(ruta_imagen, ruta_destino)

        print(f"[{i}/{total}] {nombre_archivo} -> {carpeta_final.upper()} ({confianza:.1f}%)")
        
    except Exception as e:
        print(f"[{i}/{total}] Error en {nombre_archivo}: {e}")

print("\n🎉 ¡Clasificación completada!")
