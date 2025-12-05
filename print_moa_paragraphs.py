from docx import Document
import os

def print_docx_paragraphs(docx_path):
    doc = Document(docx_path)
    for i, para in enumerate(doc.paragraphs):
        print(f"[{i}] {para.text}")

if __name__ == "__main__":
    # Update this path if needed
    docx_path = os.path.join("media", "CvSU MOA Template_Local Student Internship_revised 04212025 (2) (1).docx")
    print_docx_paragraphs(docx_path)
