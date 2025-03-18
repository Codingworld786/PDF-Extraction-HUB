import streamlit as st
import requests
import os
from PIL import Image
import time
import logging


#logs
# Logging configuration
log_file = "streamlit_logs.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(filename)s:%(lineno)d] %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="a"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Set page configuration
st.set_page_config(
    page_title="📄 DocuMagic - Smart Document Processor".encode("utf-8").decode("utf-8"),
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling
def local_css(file_name):
    """Loads local CSS for styling."""
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
        logger.info("Loaded custom CSS from %s", file_name)
    else:
        logger.warning("CSS file %s not found.", file_name)

local_css("style.css")  # Ensure you have a `style.css` file for custom styling

# API configuration
API_BASE_URL = "http://localhost:8006"  # Update with your API URL
SUPPORTED_FORMATS = ["pdf", "pptx", "docx", "png", "jpeg"]
logger.info("API base URL set to %s", API_BASE_URL)

PDF_TYPES = ["Normal", "Scanned", "Mixed"]

METHODS = {
    "Normal": ["PyMuPDF (fitz)", "PDFPlumber","docling","arker"],
    "Scanned": ["Tesseract OCR","doctr"],
    "Mixed": ["PyMuPDF", "PDFMiner", "Tesseract OCR", "Docling", "Marker", "doctr"],
    "All": ["PyMuPDF (fitz)", "PDFPlumber", "Tesseract OCR", "PyMuPDF", "docling", "Marker", "doctr"]
}

# API call function
def extract_text(api_endpoint, file_path, disable_image=False):
    """Send file to API and get extracted text."""
    try:
        logger.info("Sending request to API endpoint: %s", api_endpoint)
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{API_BASE_URL}{api_endpoint}", 
                files={"file": f}, 
                data={"disable_image": disable_image}
            )
        response.raise_for_status()
        logger.info("Received response from API.")
        return response.json()
    except requests.RequestException as e:
        logger.error("API request failed: %s", e)
        return {"error": str(e)}

# Main App
st.title("📄 DocuMagic")
st.markdown("""  
    Extract text from PDFs, images, and office documents with multiple AI-powered methods.
""")    
logger.info("Main UI rendered.")

# Sidebar with filters and method descriptions
with st.sidebar:
    st.header("\u2699\ufe0f Filter APIs")
    
    # Format selection
    selected_format = st.selectbox("Select Document Format:", ["All"] + SUPPORTED_FORMATS)
    logger.info("Selected format: %s", selected_format)
    
    selected_pdf_type = None
    if selected_format == "pdf":
        selected_pdf_type = st.selectbox("Select PDF Type:", ["All"] + PDF_TYPES)
        logger.info(f"selected pdf type: %s",selected_pdf_type)

        st.write(f"**Recommended Extraction Methods for {selected_pdf_type}:**")
        method_options = METHODS.get(selected_pdf_type, [])
        method = st.radio("Choose processing method:", method_options) if method_options else None

    st.markdown("---")
    
    st.header("\u2699\ufe0f Extraction Methods")
    method_options = {
        "PDFPlumber": "pdf_normal",
        "Tesseract OCR": "pdf_scanned",
        "PyMuPDF": "pdf_mixed",
        "Docling": "pdf_normal,pdf_mixed,pptx",
        "Marker": "pdf_normal, pdf_mixed",
        "Extract_Thinker": "pdf_normal",
        "PdfMiner": "pdf_normal",
        "pptxtomd": "pptx",
        "All_Methods": "pdf, docx, pptx, xlsx"
    }
    
    # Filter methods based on selection
    available_methods = [m for m, f in method_options.items() if selected_format in f or selected_format == "All"]
    method = st.radio("Choose processing method:", available_methods)
    
    st.markdown("---")
    st.subheader("Method Guide")
    method_info = {
        "PDFPlumber": "Best for: Digital PDFs with selectable text",
        "Tesseract OCR": "Best for: Scanned PDFs/image-based documents",
        "PyMuPDF": "Best for: Mixed PDFs with text and images",
        "Docling": "Best for: Office documents (DOCX, PPTX, XLSX)",
        "Marker": "Best for: PDF processing",
        "Extract_Thinker": "Best to chit-chat with your doc",
        "PdfMiner": "Best for Normal PDFs",
        "pptxtomd": "Best for PPT processing",
        "All_Methods": "Best for: Comparing all methods"
    }
    if method in method_info:
        st.info(method_info[method])

# Main content area
# Main content area
st.subheader("📤 Upload Your Document")
uploaded_file = st.file_uploader(" ", type=SUPPORTED_FORMATS)

if uploaded_file:
    logger.info("File uploaded: %s", uploaded_file.name)
    st.markdown("---")
    col1, col2 = st.columns([1, 3])
    with col1:
        st.subheader("📄 Document Preview")
        if uploaded_file.type.startswith('image'):
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image", use_column_width=True)
            logger.info("Image file displayed.")
        else:
            st.markdown(f"**File Name:** {uploaded_file.name}\n**File Type:** {uploaded_file.type}\n**File Size:** {uploaded_file.size//1024} KB")
            logger.info("Non-image file details displayed.")

    with col2:
        st.subheader("⚙️ Processing Options")
        if st.button(f"Process with {method}", use_container_width=True):
            temp_path = f"temp.{uploaded_file.name.split('.')[-1]}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                with st.spinner("🔍 Analyzing document content..."):
                    endpoints = {
                        "PDFPlumber": "/extract/pdfplumber",
                        "Tesseract OCR": "/extract/tesseract",
                        "PyMuPDF": "/extract/pymupdf",
                        "Docling": "/extract/docling",
                        "Marker": "/extract/marker",
                        "Extract_Thinker": "/extract/extract_thinker",
                        "PdfMiner": "/extract_pdfminer_full",
                        "pptxtomd": "/extract/pptx2md",
                        "All_Methods": "/extract/all"
                    }

                    result = extract_text(endpoints[method], temp_path)

                st.markdown("---")
                st.subheader("📜 Extraction Results")
                extracted_text = result.get("text", "No text extracted")
                st.code(extracted_text, language="text")
                logger.info("Text extraction completed.")
                
                # Handle Markdown file download for PPTX conversion
                if method == "pptxtomd" and "markdown_content" in result:
                    st.markdown(result["markdown_content"])
                    st.download_button(
                        "⬇️ Download Markdown",
                        data=result["markdown_content"],
                        file_name=result["filename"],
                        mime="text/markdown"
                    )
                elif method == "Extract_Thinker" and "extracted_data" in result:
                    st.json(result["extracted_data"])

                # Save extracted text
                output_folder = "output_folder"
                os.makedirs(output_folder, exist_ok=True)
                output_file = os.path.join(output_folder, f"{uploaded_file.name.rsplit('.', 1)[0]}_{method.replace(' ', '_')}.md")

                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(extracted_text)
                
                with open(output_file, "rb") as f:
                    st.download_button("⬇️ Download Extracted Text", f, file_name=output_file, mime="text/plain")
                
                st.success("✅ Processing completed successfully!")

            except Exception as e:
                st.error(f"❌ Error processing document: {str(e)}")
                logger.error("Error processing document: %s", e)

            finally:
                if os.path.exists(temp_path):
                    try:
                        time.sleep(1)  # Give OS time to release the file
                        os.remove(temp_path)
                        logger.info("Temporary file deleted: %s", temp_path)
                    except PermissionError:
                        st.warning(f"⚠️ Could not delete temporary file: {temp_path}. It may still be in use.")
                        logger.warning("Could not delete temporary file: %s", temp_path)