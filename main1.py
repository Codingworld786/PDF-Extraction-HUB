from fastapi import FastAPI, UploadFile, File, Query
import pdfplumber
from pdf2image import convert_from_path
import shutil
import os
import fitz  # PyMuPDF
from docling.document_converter import DocumentConverter  # docling
from marker.converters.pdf import PdfConverter
from marker.converters.table import TableConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
import deepdoctection as dd
from extract_thinker import Extractor
from extract_thinker.exceptions import ExtractThinkerError
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import StringIO
import base64
#------- OCR ------------
import pdf2image
import pytesseract
from pytesseract import Output, TesseractError
from doctr.io import DocumentFile

# Extract thinker
import os
import shutil
from fastapi import FastAPI, UploadFile, File
from dotenv import load_dotenv
from extract_thinker import Extractor, DocumentLoaderPyPdf, Contract


#logs
import logging

print(DocumentFile)
##################################################################################################################

app = FastAPI()

##################################################################################################################
# logs

import logging

log_file = "api_logs.log"

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Change to DEBUG for more logs

# Create handlers
file_handler = logging.FileHandler(log_file, mode="a")  # Appends logs
console_handler = logging.StreamHandler()  # Prints to console

# Set formatter
formatter = logging.Formatter("%(asctime)s [%(filename)s:%(lineno)d] %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger (avoid duplicates)
if not logger.hasHandlers():
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# Example log message
logger.info("Logging setup complete. Logs will be saved in api_logs.log")

##################################################################################################################
# helper functions
def handle_file_upload(file: UploadFile):
    """Handle file upload, save temporarily, and return path."""
    temp_path = f"temp_{file.filename.replace(' ', '_')}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    logging.info(f"File uploaded and saved as: {temp_path}")
    return temp_path

def save_text_as_markdown(filename: str, text: str, method: str):
    """Save extracted text as a Markdown (.md) file."""
    sanitized_filename = filename.replace(" ", "_")
    md_filename = f"{sanitized_filename}_{method}.md"
    with open(md_filename, "w", encoding="utf-8") as md_file:
        md_file.write(f"# Extracted Text ({method})\n\n{text}")
        logging.info(f"Extracted text saved as: {md_filename}")
    return md_filename

# main functions and apis
##################################################################################################################
# 1. pdf plumber
def extract_text_pdfplumber(pdf_path: str):
    """Extract text from text-based PDFs using PDFPlumber."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n" if page.extract_text() else ""
        logging.info(f"Test extracted using pdfplumber from: {pdf_path}")
    except Exception as e:
        logging.error(f"Error occur during text extraction with pdfplumber: {e}")

    return text.strip()


# api
@app.post("/extract/pdfplumber")
async def pdfplumber_extraction(file: UploadFile = File(...)):
    temp_path = handle_file_upload(file)
    text = extract_text_pdfplumber(temp_path)
    os.remove(temp_path)
    logging.info(f"Temporary file deleted: {temp_path}")
    md_filename = save_text_as_markdown(file.filename, text, "pdfplumber") if text else None
    return {"text": text or "No text extracted", "method": "PDFPlumber", "saved_as": md_filename}

##################################################################################################################
#2. pytesseract
def extract_text_tesseract(pdf_path: str):
    """Extract text from scanned PDFs using Tesseract OCR."""
    text=""
    try:
        images = convert_from_path(pdf_path)
        for img in images:
            text += pytesseract.image_to_string(img) + "\n"
        logging.info(f"Text extracted using Tesseract OCR from: {pdf_path}")
    except Exception as e:
        logging.error(f"Error extracting text with Tesseract: {e}")
    return text.strip()

#api
@app.post("/extract/tesseract")
async def tesseract_extraction(file: UploadFile = File(...)):
    temp_path = handle_file_upload(file)
    text = extract_text_tesseract(temp_path)
    os.remove(temp_path)
    md_filename = save_text_as_markdown(file.filename, text, "tesseract") if text else None
    return {"text": text or "No text extracted", "method": "Tesseract OCR", "saved_as": md_filename}
    
##################################################################################################################
#3. pymupdf        
def extract_text_pymupdf(pdf_path: str):
    """Extract text using PyMuPDF."""
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text("text") + "\n"
        logging.info(f"Text extracting using PyMuPDF: {pdf_path}")
    except Exception as e:
        logging.error(f"Error extracting text with PyMuPDF {e}")
    return text.strip()
#api
@app.post("/extract/pymupdf")
async def pymupdf_extraction(file: UploadFile = File(...)):
    temp_path = handle_file_upload(file)
    text = extract_text_pymupdf(temp_path)
    os.remove(temp_path)
    logging.info(f"Temporary file deleted: {temp_path}")
    md_filename = save_text_as_markdown(file.filename, text, "pymupdf") if text else None
    return {"text": text or "No text extracted", "method": "PyMuPDF", "saved_as": md_filename}
    
##################################################################################################################
#docling
# Docling configuration
SUPPORTED_FORMATS = ["pdf", "pptx", "docx", "xlsx", "md", "csv", "png", "jpeg", "tiff"]

def extract_text_docling(temp_path: str, filename: str):
    """Extract text using Docling."""
    logging.info(f"Starting docling extraction for file: {filename}")
    file_ext = filename.split(".")[-1].lower()
    if file_ext not in SUPPORTED_FORMATS:
        logging.warning(f"Unsupported file format: {file_ext}")
        return "Unsupported file format"
    
    converter = DocumentConverter()
    result = converter.convert(temp_path)
    logging.info(f"Successfully extracted text using Docling for file: {filename}")
    return result.document.export_to_markdown()
#api
@app.post("/extract/docling")
async def docling_extraction(file: UploadFile = File(...)):
    temp_path = handle_file_upload(file)
    text = extract_text_docling(temp_path, file.filename)
    os.remove(temp_path)
    logging.info(f"File {file.filename} processed and deleted from temp storage")
    md_filename = save_text_as_markdown(file.filename, text, "docling") if text and "Unsupported" not in text else None
    return {"text": text, "method": "Docling", "saved_as": md_filename}

##################################################################################################################
# 5.  Marker text extraction
def extract_text_marker(temp_path: str):
    """Extract text and tables using Marker."""
    logging.info(f"Starting Marker extraction for file: {temp_path}")
    text_converter = PdfConverter(artifact_dict=create_model_dict())
    table_converter = TableConverter(artifact_dict=create_model_dict())
    
    text_rendered = text_converter(temp_path)
    table_rendered = table_converter(temp_path)
    
    text, _, _ = text_from_rendered(text_rendered)
    table_text, _, _ = text_from_rendered(table_rendered)
    logging.info(f"Marker extraction completed for file: {temp_path}")
    
    return text, table_text
#api
@app.post("/extract/marker")
async def marker_extraction(file: UploadFile = File(...)):
    temp_path = handle_file_upload(file)
    text, table_text = extract_text_marker(temp_path)
    os.remove(temp_path)
    logging.info(f"File {file.filename} processed and deleted from temp storage")
    
    md_text = save_text_as_markdown(file.filename, text, "marker_text") if text else None
    md_table = save_text_as_markdown(file.filename, table_text, "marker_table") if table_text else None
    
    return {
        "text": text or "No text extracted",
        "table_text": table_text or "No table extracted",
        "saved_files": {"text": md_text, "table": md_table}
    }
##################################################################################################################
#6.  doctr
# # Doctr text extraction
# import deepdoctection as dd
# from matplotlib import pyplot as plt

# def extract_text_doctr(temp_path: str, filename: str):
#     """Extract text using Doctr."""
#     config_overwrite = [
#         "OCR.USE_DOCTR=True",
#         "OCR.USE_TESSERACT=False",
#         "TEXT_ORDERING.INCLUDE_RESIDUAL_TEXT_CONTAINER=True"
#     ]

#     analyzer = dd.get_dd_analyzer(config_overwrite=config_overwrite)
#     doc = analyzer.analyze(temp_path)
#     page_number = 1

#     markdown_filename = f"{filename.replace(' ', '_')}_doctr.md"
#     with open(markdown_filename, 'w') as markdown_file:
#         for page in doc.pages:
#             page_details = str(page)
#             if page_number == 1:
#                 markdown_file.write("# Extracted Content\n\n")
#             markdown_file.write(f"## Page {page_number}\n\n")
#             markdown_file.write(f"{page_details}\n\n")
#             page_number += 1

#     return markdown_filename


# @app.post("/extract/doctr")
# async def doctr_extraction(file: UploadFile = File(...)):
#     temp_path = handle_file_upload(file)
#     md_filename = extract_text_doctr(temp_path, file.filename)
#     os.remove(temp_path)
#     return {"method": "Doctr", "saved_as": md_filename}

from doctr.io import DocumentFile
print(DocumentFile)

# @app.post("/extract/doctr")
# async def extract_text_doctr(file: UploadFile = File(...)):
#     temp_path = handle_file_upload(file)
#     pdf_doc = DocumentFile.from_pdf(temp_path)
#     extracted_text = "\n".join([page.text for page in pdf_doc])
#     md_filename = save_text_as_markdown(file.filename, extracted_text, "doctr_pdf")
#     return {"markdown_file": md_filename}  

@app.post("extract/doctr")
async def extract_text_doctr(file: UploadFile = File(...)):
    pass

##################################################################################################################
# 7.  extract thinker

load_dotenv()
def create_dynamic_contract(field_list):
    """Dynamically create a contract class based on user-provided fields."""
    attributes = {"__annotations__": {field: str for field in field_list}}  # Explicit type annotations
    attributes["__module__"] = __name__  # Required to avoid KeyError in Pydantic
    return type("DynamicInvoiceContract", (Contract,), attributes)

def extract_text_thinker(pdf_path: str, field_list: list):
    """Extract user-specified fields from the given PDF file."""
    logging.info(f"Starting Thinker extraction for file: {pdf_path}")
    extractor = Extractor()
    extractor.load_document_loader(DocumentLoaderPyPdf())
    extractor.load_llm("gpt-4o")  # Load the required LLM

    # Dynamically create the contract class
    DynamicInvoiceContract = create_dynamic_contract(field_list)

    # Extract data using the dynamically created contract
    result = extractor.extract(pdf_path, DynamicInvoiceContract)

    # Convert extracted result into a dictionary
    extracted_data = {field: getattr(result, field, None) for field in field_list}
    logging.info(f"Thinker extraction completed for file: {pdf_path}")
    return extracted_data


@app.post("/extract/extract_thinker")
async def thinker_extraction(file: UploadFile = File(...), fields: list[str] = ["Insert field You want to extract"]):
    """Extract user-specified fields from a PDF using extract_thinker."""
    temp_path = handle_file_upload(file)
    extracted_data = extract_text_thinker(temp_path, fields)
    os.remove(temp_path)
    logging.info(f"File {file.filename} processed and deleted from temp storage")
    md_filename = save_text_as_markdown(file.filename, str(extracted_data), "extract_thinker") if extracted_data else None
    return {"extracted_data": extracted_data or "No data extracted", "method": "extract_thinker", "saved_as": md_filename}
##################################################################################################################
# 8. pdfminer

def convert_pdf_to_txt_file(pdf_path):
    """Extracts full text from a PDF file using pdfminer."""
    logging.info(f"Starting full pdf text extraction for {pdf_path}")
    rsrcmgr = PDFResourceManager()
    retstr = StringIO() 
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    with open(pdf_path, 'rb') as file:
        pages = list(PDFPage.get_pages(file))
        nb_pages = len(pages)  # Count total pages
        logging.info(f"Total Pages found: {nb_pages}")
        for page in pages:
            interpreter.process_page(page)

    text = retstr.getvalue()  # Get the full extracted text

    device.close()
    retstr.close()
    logging.info(f"Completed full PDF extraction. Extracted {len(text)} characters.")
    
    return text, nb_pages

def convert_pdf_to_txt_pages(pdf_path):
    """Extracts text from a PDF file page by page using pdfminer."""
    logging.info(f"Starting per-page PDF text extraction for {pdf_path}")
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    texts = []

    with open(pdf_path, 'rb') as file:
        retstr = StringIO()
        device = TextConverter(rsrcmgr, retstr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        pages = list(PDFPage.get_pages(file))
        nb_pages = len(pages)  # Get total number of pages
        logging.info(f"Total pages found: {nb_pages}")

        size = 0  # Keeps track of text size per page
        for c, page in enumerate(pages):
            interpreter.process_page(page)
            t = retstr.getvalue()
            if c == 0:
                texts.append(t)  # First page
            else:
                texts.append(t[size:])  # Subsequent pages get new content only
            size = len(t)  # Update size for the next iteration

        device.close()
        retstr.close()
    logging.info(f"Completed per-page PDF extraction. Extracted text from {nb_pages} pages.")
    return texts, nb_pages    

@app.post("/extract/pdfminer/pages")
async def extract_pdfminer_pages(file: UploadFile = File(...)):
    temp_path = handle_file_upload(file)
    texts, nb_pages = convert_pdf_to_txt_pages(temp_path)
    os.remove(temp_path)
    md_filename = save_text_as_markdown(file.filename, "\n".join(texts), "pdfminer") if texts else None
    return {"text": texts or "No text extracted", "pages": nb_pages, "method": "PDFMiner", "saved_as": md_filename}

@app.post("/extract/pdfminer_full")
async def extract_pdfminer_full(file: UploadFile = File(...)):
    temp_path = handle_file_upload(file)
    text, nb_pages = convert_pdf_to_txt_file(temp_path)
    os.remove(temp_path)
    md_filename = save_text_as_markdown(file.filename, text, "pdfminer") if text else None
    return {"text": text or "No text extracted", "pages": nb_pages, "method": "PDFMiner", "saved_as": md_filename}

##################################################################################################################
from pptx2md import convert, ConversionConfig
from pathlib import Path
import os

OUTPUT_FOLDER = Path(os.getcwd()) / "output"
TEMP_FOLDER = Path(os.getcwd()) / "temp"

OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
TEMP_FOLDER.mkdir(parents=True, exist_ok=True)

@app.post("/extract/pptx2md")
async def convert_pptx_to_md(file: UploadFile = File(...), disable_image: bool = False):
    logging.info(f"Processing PPTX file: {file.filename}")
    if not file.filename.endswith('.pptx'):
        logging.error("Invalid file format. Only .pptx files are supported.")
        return {"error": "Only .pptx files are supported."}
    
    try:
        temp_pptx_path = TEMP_FOLDER / file.filename
        with open(temp_pptx_path, "wb") as temp_file:
            temp_file.write(await file.read())
        
        output_md_path = OUTPUT_FOLDER / f"{Path(file.filename).stem}.md"
        image_dir = OUTPUT_FOLDER / Path(file.filename).stem / "images"
        
        if not disable_image:
            image_dir.mkdir(parents=True, exist_ok=True)
        
        config = ConversionConfig(
            pptx_path=temp_pptx_path,
            output_path=output_md_path,
            image_dir=image_dir if not disable_image else None,
            disable_notes=False,
            enable_slides=True,
            disable_image=disable_image
        )
        
        convert(config)
        os.remove(temp_pptx_path)
        
        # Read generated markdown content
        with open(output_md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        logging.info(f"PPTX conversion successfull. Markdown saved at {output_md_path}")
        
        return {
            "markdown_content": md_content,
            "filename": output_md_path.name
        }
    except Exception as e:
        logging.error(f"Error processing PPTX file: {str(e)}")
        return {"error": str(e)}


##################################################################################################################

@app.post("/extract/all")
async def extract_all(file: UploadFile = File(...)):
    temp_path = handle_file_upload(file)
    results = {}
    
    try:
        # Basic PDF extraction
        results["pdfplumber"] = extract_text_pdfplumber(temp_path)
        results["tesseract"] = extract_text_tesseract(temp_path)
        results["pymupdf"] = extract_text_pymupdf(temp_path)
        
        # Docling extraction
        results["docling"] = extract_text_docling(temp_path, file.filename)
        
        # Marker extraction
        marker_text, marker_table = extract_text_marker(temp_path)
        results["marker_text"] = marker_text
        results["marker_table"] = marker_table
        results["doctr"]=extract_text_doctr(temp_path, file.filename)
        results["extract_thinker"]=extract_text_thinker(temp_path, file.filename)
        results["extract_pdfminer_full"]=extract_pdfminer_full(temp_path, file.filename)
        results["extract_pdfminer_pages"]=extract_pdfminer_pages(temp_path, file.filename)

        
        # Save all results
        md_files = {}
        for method, text in results.items():
            if text and "Unsupported" not in text:
                md_files[method] = save_text_as_markdown(file.filename, text, method)
        
        return {"results": results, "saved_files": md_files}
    
    finally:
        os.remove(temp_path)

@app.get("/supported-formats")
async def supported_formats():
    return {"supported_formats": SUPPORTED_FORMATS}