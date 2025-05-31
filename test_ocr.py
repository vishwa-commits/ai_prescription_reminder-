import pytesseract
from PIL import Image
import os

# Set the path (same as in your app.py)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Create a simple test image
def create_test_image():
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGB', (200, 50), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((10, 10), "Test Prescription 500mg", fill=(0, 0, 0))
    img.save('test.png')

def test_ocr():
    if not os.path.exists('test.png'):
        create_test_image()
    
    text = pytesseract.image_to_string(Image.open('test.png'))
    print(f"OCR Output: {text}")
    assert "500mg" in text, "OCR test failed!"
    print("✓ Tesseract is working correctly!")

if __name__ == "__main__":
    test_ocr()