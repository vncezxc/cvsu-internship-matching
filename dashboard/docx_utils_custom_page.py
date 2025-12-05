from docx import Document
from docx.oxml.ns import qn

def extract_editable_runs_by_custom_markers(docx_path, markers):
    """
    Splits the DOCX into pages based on custom marker phrases.
    Returns a list of pages, each page is a list of paragraphs, each as a list of dicts: {text, editable, run_idx, para_idx}.
    """
    doc = Document(docx_path)
    pages = []
    current_page = []
    para_idx = 0
    marker_idx = 0
    marker_count = len(markers)
    # Only process paragraphs, not tables
    for para in doc.paragraphs:
        para_text = para.text.strip()
        para_runs = []
        for idx, run in enumerate(para.runs):
            is_underlined = run.underline is True
            is_highlighted = False
            is_shaded = False
            if run._element.rPr is not None:
                # Highlight detection
                highlight = run._element.rPr.find(qn('w:highlight'))
                if highlight is not None:
                    val = highlight.get(qn('w:val'))
                    if val and val.lower() != 'none':
                        is_highlighted = True
                # Character shading detection
                shading = run._element.rPr.find(qn('w:shd'))
                if shading is not None:
                    fill = shading.get(qn('w:fill'))
                    if fill and fill.lower() != 'auto' and fill != 'FFFFFF':
                        is_shaded = True
            para_runs.append({
                'text': run.text,
                'editable': is_underlined or is_highlighted or is_shaded,
                'run_idx': idx,
                'para_idx': para_idx
            })
        if para_runs:
            current_page.append(para_runs)
        # If this paragraph matches a marker, start a new page
        if marker_idx < marker_count and markers[marker_idx] in para_text:
            if current_page:
                pages.append(current_page)
            current_page = []
            marker_idx += 1
        para_idx += 1
    # Do NOT process tables at all (table content is not editable)
    if current_page:
        pages.append(current_page)
    return pages
