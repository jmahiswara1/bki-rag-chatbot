import os
import fitz
import re
import ollama
import pytesseract
from PIL import Image
import io
from src.core.models import Chunk
from src.core.config import settings

def process_figures(pdf_path: str, pages: list[int] = None) -> list[Chunk]:
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
        
    doc = fitz.open(pdf_path)
    page_indices = pages if pages is not None else range(len(doc))
    
    chunks = []
    figure_pattern = re.compile(r'Fig\.?\s*(\d+\.\d+)')
    
    client = ollama.Client(host=settings.ollama_host)
    
    for idx in page_indices:
        page = doc[idx]
        image_list = page.get_images(full=True)
        if not image_list:
            continue
            
        text = page.get_text("text")
        
        figure_no = None
        caption = "Figure"
        for line in text.split('\n'):
            m = figure_pattern.search(line)
            if m:
                figure_no = m.group(1)
                caption = line.strip()
                break
                
        section_no = None
        section_title = None
        lines = text.split("\n")
        for i, line in enumerate(lines[:15]):
            if line.startswith("Sec "):
                try:
                    section_no = int(line.replace("Sec ", "").strip())
                    if i + 1 < len(lines):
                        section_title = lines[i+1].strip()
                    break
                except ValueError:
                    pass
            elif line.strip() == "Sec":
                try:
                    section_no = int(lines[i+1].strip())
                    section_title = lines[i+2].strip()
                    break
                except (ValueError, IndexError):
                    pass
                    
        if not section_no:
            section_no = 0
            section_title = "Unknown"
            
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            image = Image.open(io.BytesIO(image_bytes))
            ocr_text = pytesseract.image_to_string(image).strip()
            
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            png_bytes = img_byte_arr.getvalue()
            
            import base64
            resp = client.generate(
                model=settings.vlm_model,
                prompt='Describe this diagram concisely.',
                images=[base64.b64encode(png_bytes).decode('utf-8')],
                options={'num_predict': 128, 'num_ctx': 1024}
            )
            vlm_desc = resp['response'].strip()
            
            header = f"[Sec {section_no} {section_title} | Fig {figure_no}]" if figure_no else f"[Sec {section_no} {section_title} | Figure]"
            content = f"{header}\nCaption: {caption}\nOCR: {ocr_text}\nDescription: {vlm_desc}".replace("\x00", "")
            
            chunks.append(Chunk(
                section_no=section_no,
                section_title=section_title,
                content_type="figure",
                page_start=idx + 1,
                page_end=idx + 1,
                content=content,
                figure_no=figure_no
            ))
            
    doc.close()
    return chunks
