# Image Text Extractor

A web application that extracts text from images using Tesseract OCR.

## Prerequisites

1. Install Tesseract OCR:
   - Windows: Download and install from https://github.com/UB-Mannheim/tesseract/wiki
   - Make sure to add Tesseract to your system PATH

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. Start the Flask server:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to `http://localhost:5000`

## Usage

1. Click on the upload area or drag and drop an image
2. Wait for the text extraction to complete
3. The extracted text will be displayed below the upload area

## Features

- Drag and drop image upload
- Support for various image formats
- Real-time text extraction
- Error handling and user feedback
- Clean and modern UI 