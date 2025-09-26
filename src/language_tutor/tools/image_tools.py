import os
from PIL import Image, ImageDraw, ImageFont
import textwrap
import re
from difflib import ndiff

def text_to_image(text: str, output_path: str) -> str | None:
    """
    Genera una imagen de feedback con dos secciones a partir de un texto estructurado.

    :param text: El texto a renderizar en la imagen.
    :param output_path: La ruta donde se guardará la imagen generada.
    :return: La ruta al archivo de imagen si se generó correctamente, o None.
    """
    # --- Configuración de Estilo ---
    WIDTH = 600
    PADDING = 30
    BOX_SPACING = 20
    CORNER_RADIUS = 15

    # Colores
    TOP_BOX_BG = "#434C5E"  # Gris Oxford (Nord)
    BOTTOM_BOX_BG = "#FFFFFF"
    FEEDBACK_TEXT_COLOR = "#EBCB8B"  # Amarillo (Nord)
    PERCENTAGE_TEXT_COLOR = "#A3BE8C"  # Verde (Nord)
    RESPONSE_ONLY_BG_COLOR = "#FFFBEA" # Un amarillo muy claro
    CORRECTED_TEXT_COLOR = "#000000"
    INCORRECT_WORD_BG = "#F34A07"  # Rojo (Nord)
    INCORRECT_WORD_TEXT = "#FFFFFF"

    try:
        # Intentar usar fuentes comunes en Linux (como en la Raspberry Pi)
        font_regular = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=20)
        font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size=20)
    except IOError:
        try:
            # Si falla, intentar con fuentes de Windows
            font_regular = ImageFont.truetype("arial.ttf", size=20)
            font_bold = ImageFont.truetype("arialbd.ttf", size=20)
        except IOError:
            # Como último recurso, usar la fuente por defecto (sin negritas)
            print("Warning: Custom fonts not found. Falling back to default font.")
            font_regular = ImageFont.load_default()
            font_bold = ImageFont.load_default()

    # 1. Parsear el texto del agente
    original_sent = re.search(r'Original:\s*"(.*?)"', text, re.DOTALL)
    corrected_sent = re.search(r'Corregido:\s*"(.*?)"', text, re.DOTALL)
    # La línea de feedback ahora es estática, no necesitamos parsearla.
    tip_line = re.search(r'Tip:\s*(.*)', text, re.DOTALL)

    # La sección 'Corregido' es ahora opcional.
    # Si no hay errores, no existirá.
    has_correction = corrected_sent is not None

    original_sent_text = original_sent.group(1) if original_sent else ""
    corrected_sent_text = corrected_sent.group(1) if has_correction else ""
    tip_text = (tip_line.group(1) if tip_line else "").replace('\\n', '\n')

    # --- Dibujar la caja superior (Feedback) ---
    top_box_height = 80
    top_img = Image.new('RGBA', (WIDTH, top_box_height), (0, 0, 0, 0))
    top_draw = ImageDraw.Draw(top_img)
    top_draw.rounded_rectangle(((0, 0), (WIDTH, top_box_height)), radius=CORNER_RADIUS, fill=TOP_BOX_BG)
    
    feedback_label = "Feedback"
    label_width = top_draw.textlength(feedback_label, font=font_bold)
    top_draw.text(((WIDTH - label_width) / 2, (top_box_height - font_bold.getbbox(feedback_label)[3]) / 2), feedback_label, font=font_bold, fill=FEEDBACK_TEXT_COLOR)

    # --- Dibujar la caja inferior (Corrección) ---
    words_to_draw = []
    if has_correction:
        # Encontrar las diferencias entre la frase original y la corregida
        diff = ndiff(original_sent_text.split(), corrected_sent_text.split())
        for item in diff:
            code = item[0]
            word = item[2:]
            if code == ' ': # La palabra es correcta y está en ambas
                words_to_draw.append({'text': word, 'type': 'correct'})
            elif code == '-': # La palabra fue eliminada (incorrecta)
                words_to_draw.append({'text': word, 'type': 'incorrect'})
            elif code == '+': # La palabra fue añadida (parte de la corrección)
                # No la dibujamos como una palabra separada, es parte de la frase final
                pass
    else:
        # Si no hay corrección, todas las palabras son correctas.
        words_to_draw = [{'text': word, 'type': 'correct'} for word in original_sent_text.split()]

    # Calcular el alto necesario para la caja inferior
    # Usamos un ancho de caracteres aproximado para el text wrapper
    wrap_width = 45 
    original_lines = textwrap.wrap(original_sent_text, width=wrap_width)
    corrected_lines = textwrap.wrap(corrected_sent_text, width=wrap_width) if has_correction else []
    tip_lines = textwrap.wrap(tip_text, width=wrap_width) if tip_text else []
    line_height = font_regular.getbbox("A")[3] + 15

    # Dibujamos en un lienzo temporal muy alto para medir el contenido real.
    temp_height = 2000
    bottom_img = Image.new('RGBA', (WIDTH, temp_height), (0, 0, 0, 0))
    bottom_draw = ImageDraw.Draw(bottom_img)
    bottom_draw.rounded_rectangle(((0, 0), (WIDTH, temp_height)), radius=CORNER_RADIUS, fill=BOTTOM_BOX_BG)

    # Dibujar las palabras en la caja inferior
    x, y = PADDING, PADDING
    space_width = bottom_draw.textlength(" ", font=font_regular)
    
    # --- Sección Frase Original ---
    bottom_draw.text((x, y), "Frase Original:", font=font_bold, fill=CORRECTED_TEXT_COLOR)
    y += line_height

    # Dibujar la frase original con errores resaltados
    for word_info in words_to_draw:
        word = word_info['text']
        word_font = font_regular

        # Si la palabra se sale de la línea, saltar a la siguiente
        if x + bottom_draw.textlength(word, font=word_font) > WIDTH - PADDING:
            x = PADDING
            y += line_height

        if word_info['type'] == 'incorrect':
            # Dibujar un fondo rojo para la palabra incorrecta
            bbox = bottom_draw.textbbox((x, y), word, font=word_font)
            # Añadimos un pequeño margen al fondo
            bbox = (bbox[0] - 5, bbox[1] - 2, bbox[2] + 5, bbox[3] + 2)
            bottom_draw.rectangle(bbox, fill=INCORRECT_WORD_BG)
            bottom_draw.text((x, y), word, font=word_font, fill=INCORRECT_WORD_TEXT)
        else:
            bottom_draw.text((x, y), word, font=word_font, fill=CORRECTED_TEXT_COLOR)
        
        x += bottom_draw.textlength(word, font=word_font) + space_width
    
    # Avanzar a la siguiente sección
    y += line_height
    bottom_draw.line([(PADDING, y), (WIDTH - PADDING, y)], fill="#D8DEE9", width=1)
    y += PADDING // 2

    # --- Sección Frase Corregida ---
    if has_correction:
        bottom_draw.text((PADDING, y), "Corregido:", font=font_bold, fill=CORRECTED_TEXT_COLOR)
        y += line_height
        for line in corrected_lines:
            bottom_draw.text((PADDING, y), line, font=font_regular, fill=CORRECTED_TEXT_COLOR)
            y += line_height

        # Avanzar a la siguiente sección
        y += PADDING // 2
        bottom_draw.line([(PADDING, y), (WIDTH - PADDING, y)], fill="#D8DEE9", width=1)
        y += PADDING // 2

    # --- Sección Consejo (Tip) ---
    if tip_lines:
        tip_start_y = y
        tip_section_height = (len(tip_lines) + 1) * line_height  # +1 para la etiqueta "Tip:"
        bottom_draw.rectangle([(0, tip_start_y - 15), (WIDTH, tip_start_y + tip_section_height)], fill=RESPONSE_ONLY_BG_COLOR) # Reutilizamos el color amarillo
        bottom_draw.text((PADDING, y), "Tip:", font=font_bold, fill=CORRECTED_TEXT_COLOR)
        y += line_height
        for line in tip_lines:
            bottom_draw.text((PADDING, y), line, font=font_regular, fill=CORRECTED_TEXT_COLOR)
            y += line_height
        
        # Avanzar a la siguiente sección
        y += PADDING // 2
        bottom_draw.line([(PADDING, y), (WIDTH - PADDING, y)], fill="#D8DEE9", width=1)
        y += PADDING // 2
    
    # --- Recortar la imagen a su altura real ---
    # La altura final es la última posición 'y' más el padding inferior.
    final_bottom_height = y + PADDING
    bottom_img = bottom_img.crop((0, 0, WIDTH, final_bottom_height))
    bottom_box_height = final_bottom_height

    # --- Combinar ambas cajas en una imagen final ---
    # Usamos la altura precalculada de la caja inferior que ya incluye todos los espacios.
    total_height = top_box_height + BOX_SPACING + bottom_box_height
    final_img = Image.new('RGBA', (WIDTH, total_height), (0, 0, 0, 0))
    final_img.paste(top_img, (0, 0))
    final_img.paste(bottom_img, (0, top_box_height + BOX_SPACING))

    # Convertir a RGB antes de guardar como JPEG/PNG si es necesario
    final_img_rgb = final_img.convert('RGB')
    final_img_rgb.save(output_path)
    return output_path

def text_to_simple_image(text: str, output_path: str) -> str | None:
    """
    Genera una imagen simple con un texto, ideal para mostrar la respuesta del bot.

    :param text: El texto a renderizar en la imagen.
    :param output_path: La ruta donde se guardará la imagen generada.
    :return: La ruta al archivo de imagen si se generó correctamente, o None.
    """
    # --- Configuración de Estilo ---
    WIDTH = 600
    PADDING = 30
    BG_COLOR = "#FFFBEA" # Amarillo muy claro
    TEXT_COLOR = "#000000"

    try:
        # Intentar usar fuentes comunes en Linux
        font_regular = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=18)
    except IOError:
        try:
            # Si falla, intentar con fuentes de Windows
            font_regular = ImageFont.truetype("arial.ttf", size=18)
        except IOError:
            # Como último recurso, usar la fuente por defecto
            font_regular = ImageFont.load_default()

    # Usamos un ancho menor para que el bloque de texto sea más angosto y centrado.
    response_lines = textwrap.wrap(text, width=40)
    
    # Medimos las dimensiones del bloque de texto antes de crear la imagen final.
    dummy_img = Image.new('RGB', (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    max_line_width = 0
    if response_lines:
        max_line_width = max(dummy_draw.textlength(line, font=font_regular) for line in response_lines)

    line_height = font_regular.getbbox("A")[3] + 15
    text_block_height = (len(response_lines) * line_height) - (line_height - font_regular.getbbox("A")[3])
    
    # Creamos la imagen final con el tamaño exacto del texto + padding.
    final_width = int(max_line_width) + (2 * PADDING)
    final_height = int(text_block_height) + (2 * PADDING)
    final_img = Image.new('RGB', (final_width, final_height), BG_COLOR)
    draw = ImageDraw.Draw(final_img)
    
    y = PADDING
    for line in response_lines:
        draw.text((PADDING, y), line, font=font_regular, fill=TEXT_COLOR)
        y += line_height
    
    final_img.save(output_path)
    return output_path