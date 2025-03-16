from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from PyPDF2 import PdfReader
from transformers import pipeline
import pytesseract
from PIL import Image
import spacy
import io
import fitz  # PyMuPDF (no poppler)
import re
from googletrans import Translator
from textblob import TextBlob
from docx import Document

# Initialize FastAPI app
app = FastAPI()

# Load spaCy model for keyword extraction
nlp = spacy.load("en_core_web_sm")

# Initialize Hugging Face models
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
qa_pipeline = pipeline("question-answering")
translator = Translator()

# Function to check file type
def is_pdf(file):
    return file.filename.lower().endswith(".pdf")

def is_docx(file):
    return file.filename.lower().endswith(".docx")

# Extract text from a standard (non-scanned) PDF
def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.file.read(), filetype="pdf")
    text = "".join([page.get_text("text") or "" for page in doc])
    return text

# Convert PDF pages to images for OCR
def convert_pdf_to_images(file):
    images = []
    pdf_document = fitz.open(stream=file.file.read(), filetype="pdf")
    
    for page in pdf_document:
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)

    return images

# Extract text from scanned PDFs using OCR
def extract_text_from_images(file):
    images = convert_pdf_to_images(file)
    extracted_text = "\n".join([pytesseract.image_to_string(img) for img in images])
    return extracted_text

# Extract text from DOCX (Word files)
def extract_text_from_docx(file):
    doc = Document(io.BytesIO(file.file.read()))
    return "\n".join([para.text for para in doc.paragraphs])

# Process document (PDF, DOCX, or scanned)
def process_document(file):
    if is_pdf(file):
        text = extract_text_from_pdf(file)
        return text if text.strip() else extract_text_from_images(file)  # If empty, use OCR
    elif is_docx(file):
        return extract_text_from_docx(file)
    else:
        return file.file.read().decode("utf-8")

# Split text into smaller chunks
def split_text(text, max_chunk_size=1000):
    words, chunks, current_chunk = text.split(), [], []
    
    for word in words:
        current_chunk.append(word)
        if len(" ".join(current_chunk)) > max_chunk_size:
            chunks.append(" ".join(current_chunk[:-1]))
            current_chunk = [word]

    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

# Summarize text and return different formats
def summarize_text(text, max_length=150, min_length=50):
    summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)[0]['summary_text']
    
    bullet_points = "• " + summary.replace(". ", ".\n• ")  # Convert to bullet points
    faq_format = f"Q: What is this document about?\nA: {summary}"  # FAQ format
    
    return {"plain": summary, "bullets": bullet_points, "faq": faq_format}

# Extract keywords from text using spaCy
def extract_keywords(text):
    doc = nlp(text)
    return list(set(ent.text for ent in doc.ents if ent.label_ in ["LAW", "DATE", "ORG", "PERSON", "GPE"]))

# Highlight keywords in text
def highlight_keywords(summary, keywords):
    for keyword in keywords:
        summary = summary.replace(keyword, f"<b>{keyword}</b>")
    return summary

# Extract legal citations from text
def extract_citations(text):
    pattern = r"(Section\s\d+|Article\s\d+|Act\s\d{4})"
    return list(set(re.findall(pattern, text)))

# Compute readability score using TextBlob
def readability_score(text):
    blob = TextBlob(text)
    return blob.sentiment.polarity  # Rough indicator of complexity

# Translate summary into different languages
def translate_summary(summary, target_language="hi"):  # Default: Hindi
    return translator.translate(summary, dest=target_language).text

# NLP-based Question-Answering
def answer_question(question, text):
    return qa_pipeline(question=question, context=text)["answer"]

# Summarize document
def summarize_document(file):
    text = process_document(file)
    chunks = split_text(text)
    summaries = [summarize_text(chunk) for chunk in chunks]
    combined_summary = " ".join([s["plain"] for s in summaries])
    
    return {
        "plain": combined_summary,
        "bullets": " ".join([s["bullets"] for s in summaries]),
        "faq": " ".join([s["faq"] for s in summaries])
    }

# API Endpoint for Summarization
@app.post("/summarize/")
async def summarize(file: UploadFile = File(...), language: str = "en"):
    summary_dict = summarize_document(file)
    keywords = extract_keywords(summary_dict["plain"])
    highlighted_summary = highlight_keywords(summary_dict["plain"], keywords)
    citations = extract_citations(summary_dict["plain"])
    readability = readability_score(summary_dict["plain"])
    
    translated_summary = translate_summary(highlighted_summary, language) if language != "en" else highlighted_summary

    return {
        "summary": translated_summary,
        "bullets": summary_dict["bullets"],
        "faq": summary_dict["faq"],
        "keywords": keywords,
        "citations": citations,
        "readability_score": readability
    }

# API Endpoint for NLP Question-Answering
@app.post("/ask/")
async def ask(file: UploadFile = File(...), question: str = ""):
    text = process_document(file)
    answer = answer_question(question, text)
    
    return {"question": question, "answer": answer}
