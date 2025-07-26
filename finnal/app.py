from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import pytesseract
from PIL import Image
import os
from transformers import pipeline
from models import User
from config import Config
import pandas as pd
from werkzeug.utils import secure_filename
import time
from medicine_dataset.medicine_search import search_medicine

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'.\te\tesseract.exe'  # Path to Tesseract executable

app = Flask(__name__)
app.config.from_object(Config)

# Initialize the summarization pipeline
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure upload folder
UPLOAD_FOLDER = os.path.join('static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed file extensions for profile images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Load medicine dataset
MEDICINE_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'medicien', 'medicine_dataset.csv')

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.get_by_username(username)
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')
        gmail = request.form.get('gmail')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if User.get_by_username(username):
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if User.get_by_gmail(gmail):
            flash('Gmail already registered', 'error')
            return render_template('register.html')
        
        if not gmail.endswith('@gmail.com'):
            flash('Please enter a valid Gmail address', 'error')
            return render_template('register.html')
        
        # Handle profile image upload
        profile_image = None
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file.filename != '':
                if file and allowed_file(file.filename):
                    # Secure the filename
                    filename = secure_filename(file.filename)
                    # Add timestamp to make filename unique
                    filename = f"{int(time.time())}_{filename}"
                    # Save the file
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    profile_image = filename
        
        user = User(username=username, name=name, gmail=gmail, password=password, profile_image=profile_image)
        user.save()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
            return render_template('edit_profile.html')
        
        if new_password:
            if new_password != confirm_password:
                flash('New passwords do not match', 'error')
                return render_template('edit_profile.html')
            current_user.password_hash = generate_password_hash(new_password)
        
        current_user.email = email
        current_user.save()
        
        flash('Profile updated successfully', 'success')
        return redirect(url_for('profile'))
    
    return render_template('edit_profile.html')

@app.route('/summarize')
@login_required
def summarize():
    return render_template('summarize.html')

@app.route('/extract', methods=['POST'])
@login_required
def extract_text():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # Read the image
        image = Image.open(file)
        
        # Extract text using pytesseract
        extracted_text = pytesseract.image_to_string(image)
        
        # Summarize the text if it's not empty
        summary = ""
        if extracted_text.strip():
            # Split text into chunks if it's too long (BART has a max input length)
            max_chunk_length = 1024
            chunks = [extracted_text[i:i + max_chunk_length] for i in range(0, len(extracted_text), max_chunk_length)]
            
            summaries = []
            for chunk in chunks:
                if len(chunk.strip()) > 100:  # Only summarize chunks with substantial content
                    summary_result = summarizer(chunk, max_length=130, min_length=30, do_sample=False)
                    summaries.append(summary_result[0]['summary_text'])
            
            summary = " ".join(summaries)
        
        return jsonify({
            'text': extracted_text,
            'summary': summary
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/summarize', methods=['POST'])
@login_required
def summarize_text():
    try:
        data = request.get_json()
        text = data.get('text', '')
        summary_type = data.get('type', 'concise')
        length = int(data.get('length', 50))

        if not text:
            return jsonify({'error': 'No text provided'}), 400

        # Split text into chunks if it's too long (BART has a max input length)
        max_chunk_length = 1024
        chunks = [text[i:i + max_chunk_length] for i in range(0, len(text), max_chunk_length)]
        
        summaries = []
        for chunk in chunks:
            if len(chunk.strip()) > 100:  # Only summarize chunks with substantial content
                # Adjust max_length based on the requested length percentage
                max_length = int(len(chunk) * (length / 100))
                min_length = max(int(max_length * 0.3), 30)  # At least 30% of max_length
                
                summary_result = summarizer(chunk, max_length=max_length, min_length=min_length, do_sample=False)
                summaries.append(summary_result[0]['summary_text'])
        
        summary = " ".join(summaries)

        # Format summary based on type
        if summary_type == 'bullet':
            # Split into sentences and add bullet points
            sentences = summary.split('. ')
            summary = '\n• ' + '\n• '.join(sentences)
        elif summary_type == 'detailed':
            # Keep the summary as is, just ensure proper spacing
            summary = summary.replace('. ', '.\n\n')

        return jsonify({
            'summary': summary,
            'processing_time': 0  # You can add actual processing time if needed
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/drug')
def drug():
    return render_template('drug.html')

@app.route('/api/medicine/<name>')
def get_medicine(name):
    medicine = search_medicine(name)
    if medicine:
        return jsonify(medicine)
    return jsonify({"error": "Medicine not found"}), 404

@app.route('/medicine/<name>')
def get_medicine_info(name):
    try:
        # Check if file exists
        if not os.path.exists(MEDICINE_CSV_PATH):
            print(f"Error: CSV file not found at {MEDICINE_CSV_PATH}")
            return jsonify({'error': 'Medicine database not available'}), 500

        # Read the CSV file
        medicine_df = pd.read_csv(MEDICINE_CSV_PATH)
        
        # Clean and prepare the search term
        search_term = name.lower().strip()
        
        # Create search mask for name, generic name, and brand name
        search_mask = (
            medicine_df['name'].str.lower().str.contains(search_term, na=False) |
            medicine_df['generic_name'].str.lower().str.contains(search_term, na=False) |
            medicine_df['brand_name'].str.lower().str.contains(search_term, na=False)
        )
        
        # Get matching medicines
        matching_medicines = medicine_df[search_mask]
        
        if matching_medicines.empty:
            return jsonify({'error': 'Medicine not found'}), 404
        
        # Get the first matching medicine
        medicine_info = matching_medicines.iloc[0]
        
        # Create response with all available information
        response = {
            'name': str(medicine_info.get('name', '')),
            'generic_name': str(medicine_info.get('generic_name', '')),
            'brand_name': str(medicine_info.get('brand_name', '')),
            'manufacturer': str(medicine_info.get('manufacturer', '')),
            'category': str(medicine_info.get('category', '')),
            'description': str(medicine_info.get('description', '')),
            'uses': str(medicine_info.get('uses', '')),
            'side_effects': str(medicine_info.get('side_effects', '')),
            'dosage': str(medicine_info.get('dosage', '')),
            'storage': str(medicine_info.get('storage', '')),
            'precautions': str(medicine_info.get('precautions', '')),
            'interactions': str(medicine_info.get('interactions', '')),
            'how_to_use': str(medicine_info.get('how_to_use', ''))
        }
        
        # Clean up the response by removing empty fields
        response = {k: v for k, v in response.items() if v and v.strip()}
        
        return jsonify(response)
    except Exception as e:
        print(f"Error in get_medicine_info: {str(e)}")
        return jsonify({'error': 'Internal server error. Please try again.'}), 500

@app.route('/api/medicine/suggestions/<query>')
def get_medicine_suggestions(query):
    try:
        medicines = load_medicines()
        query = query.lower()
        
        # Search for medicines that match the query
        suggestions = []
        for medicine in medicines:
            if (query in medicine['name'].lower() or 
                query in medicine['generic_name'].lower() or 
                query in medicine['brand_name'].lower()):
                suggestions.append({
                    'name': medicine['name'],
                    'generic_name': medicine['generic_name'],
                    'brand_name': medicine['brand_name'],
                    'category': medicine['category']
                })
        
        # Limit to 5 suggestions
        suggestions = suggestions[:5]
        
        return jsonify({'suggestions': suggestions})
    except Exception as e:
        print(f"Error in get_medicine_suggestions: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/update_profile_image', methods=['POST'])
@login_required
def update_profile_image():
    if 'profile_image' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('profile'))
    
    file = request.files['profile_image']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('profile'))
    
    if file and allowed_file(file.filename):
        # Secure the filename and add user ID to make it unique
        filename = secure_filename(file.filename)
        filename = f"{current_user.get_id()}_{filename}"
        
        # Save the file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Update user's profile image in database
        current_user.profile_image = filename
        current_user.save()
        
        flash('Profile image updated successfully', 'success')
    else:
        flash('Invalid file type. Please upload a PNG, JPG, or JPEG image.', 'error')
    
    return redirect(url_for('profile'))

if __name__ == '__main__':
    app.run(debug=True) 