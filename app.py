import os
from flask import Flask, request, render_template, jsonify, send_file
from werkzeug.utils import secure_filename
import pytesseract
import cv2
import re
import numpy as np

app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(__file__), '../templates'),
            static_folder=os.path.join(os.path.dirname(__file__), '../static'))

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Tesseract path (update as needed)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image_path):
    try:
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Invalid image file")
            
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Noise reduction
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # Binarization
        _, processed = cv2.threshold(enhanced, 0, 255, 
                                   cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Save processed image for debugging
        debug_path = os.path.join(app.config['UPLOAD_FOLDER'], "processed.png")
        cv2.imwrite(debug_path, processed)
        
        return processed
    except Exception as e:
        print(f"Preprocessing error: {str(e)}")
        return None

def extract_medicines(text):
    # Enhanced medicine pattern with duration and instructions
    medicine_pattern = re.compile(
        r'(?P<name>[A-Z][a-zA-Z-]+)\s+'  # Medicine name (capitalized)
        r'(?P<dose>\d+\s*(?:mg|mcg|g|ml|tablet|tab|cap|capsule)s?)\s*'  # Dose
        r'(?:(?P<frequency>\d+\s*(?:times|X|x|\/)\s*(?:daily|day|d|week|wk|hour|hr))?[\s,-]*'  # Frequency
        r'(?P<duration>\d+\s*(?:days|day|d|weeks|wk|months|mon|m))?[\s,-]*'  # Duration
        r'(?P<instructions>(?:before|after|with)\s*(?:food|meal|breakfast|lunch|dinner|bedtime)?)?)',  # Instructions
        re.IGNORECASE
    )
    
    medicines = []
    for match in medicine_pattern.finditer(text):
        med = {
            "name": match.group("name").strip(),
            "dose": match.group("dose").strip() if match.group("dose") else "1 tablet",
            "frequency": match.group("frequency").strip() if match.group("frequency") else "1 time daily",
            "duration": match.group("duration").strip() if match.group("duration") else "7 days",
            "instructions": match.group("instructions").strip() if match.group("instructions") else "after food"
        }
        medicines.append(med)
    
    return medicines or [{
        "name": "No medicines detected", 
        "dose": "", 
        "frequency": "",
        "duration": "",
        "instructions": ""
    }]
    

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if 'image' not in request.files:
            return render_template("index.html", error="No file selected")
            
        file = request.files['image']
        if file.filename == '':
            return render_template("index.html", error="No file selected")
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            processed_img = preprocess_image(filepath)
            if processed_img is None:
                return render_template("index.html", error="Error processing image")
                
            try:
                text = pytesseract.image_to_string(processed_img)
                print("Raw OCR Output:", text)  # Debug print
                medicines = extract_medicines(text)
                return render_template("index.html", medicines=medicines)
            except Exception as e:
                return render_template("index.html", error=f"OCR error: {str(e)}")
                
    return render_template("index.html")
@app.route('/favicon.ico')
def ignore_favicon():
    return "", 204  # No Content

@app.route("/upload", methods=["POST"])
def upload():
    if 'image' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
        
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400
        
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        processed_img = preprocess_image(filepath)
        if processed_img is None:
            return jsonify({"error": "Image processing failed"}), 500
            
        text = pytesseract.image_to_string(processed_img)
        medicines = extract_medicines(text)
        
        return jsonify({
            "medicines": medicines,
            "ocr_text": text if not medicines else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/debug_image")
def debug_image():
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], "processed.png")
    if os.path.exists(image_path):
        return send_file(image_path, mimetype='image/png')
    return "No image found"

if __name__ == "__main__":
    app.run(debug=True)