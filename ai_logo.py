import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, storage, auth
import uuid
import requests
from PIL import Image
import io
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Firebase
def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS_PATH"))  # Path from environment variable
        firebase_admin.initialize_app(cred, {'storageBucket': os.getenv("FIREBASE_STORAGE_BUCKET")})  # Bucket from environment variable
        st.session_state.firebase_initialized = True

# User Authentication Functions
def authenticate_user(email, password):
    try:
        user = auth.get_user_by_email(email)
        st.session_state.user_email = email
        st.session_state.logged_in = True
        st.success(f"Welcome back, {email}!")
    except Exception as e:
        st.error("Authentication failed. Please check your credentials.")

def create_user(email, password):
    try:
        auth.create_user(email=email, password=password)
        st.success("Account created successfully! You can now log in.")
    except Exception as e:
        st.error(f"Error creating user: {e}")

# Firestore Functions
def save_logo_metadata(user_email, title, description, file_url):
    db = firestore.client()
    db.collection("users").document(user_email).collection("logos").add({
        "title": title,
        "description": description,
        "file_url": file_url,
        "timestamp": firestore.SERVER_TIMESTAMP,
    })

def fetch_user_logos(user_email):
    db = firestore.client()
    logos = db.collection("users").document(user_email).collection("logos").stream()
    return [{"id": logo.id, **logo.to_dict()} for logo in logos]

# Firebase Storage Functions
def upload_logo_to_storage(file_data, user_email):
    bucket = storage.bucket()
    file_name = f"logos/{user_email}/{uuid.uuid4()}.png"
    blob = bucket.blob(file_name)
    blob.upload_from_file(file_data, content_type="image/png")
    return blob.public_url

# New Function: Generate Logo Using API
def generate_logo_api(title, description, theme, color_palette):
    api_url = "https://api-inference.huggingface.co/models/strangerzonehf/Flux-Midjourney-Mix2-LoRA"
    headers = {"Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY')}"}
    payload = {
        "inputs": f"Create a logo with the title as '{title}' and description as '{description}' in a perfect {theme} theme with a  accurate {color_palette} color palette to impress the users."
    }
    response = requests.post(api_url, headers=headers, json=payload)

    if response.status_code == 200:
        image_data = io.BytesIO(response.content)  # Assuming API returns raw image data
        return Image.open(image_data)
    else:
        st.error("Failed to generate logo. Please try again.")
        return None

# Streamlit Pages
def login_page():
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        authenticate_user(email, password)

def signup_page():
    st.title("Sign Up")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Create Account"):
        create_user(email, password)

def logo_generation_page():
    st.title("Logo Generator")
    title = st.text_input("Enter Logo Title")
    description = st.text_area("Enter Logo Description")
    theme = st.selectbox("Select Theme", ["Modern", "Cartoon", "Basic", "Aesthetic","Trendy","Real","Alientheme"])
    color_palette = st.radio("Select Color Palette", ["Bright", "Pastel", "Dark", "Neutral","Colourful","black and White"])
    
    if st.button("Generate Logo"):
        with st.spinner("Generating your logo..."):
            logo_image = generate_logo_api(title, description, theme, color_palette)

        if logo_image:
            st.image(logo_image, caption="Generated Logo", use_container_width=True)

            # Save the image to a BytesIO buffer for downloading
            with io.BytesIO() as image_buffer:
                logo_image.save(image_buffer, format="PNG")
                image_buffer.seek(0)

                # Create a download button
                st.download_button(
                    label="Download Logo",
                    data=image_buffer,
                    file_name=f"{title.replace(' ', '_')}_logo.png",
                    mime="image/png"
                )

def user_home_page():
    st.title("My Logos")
    logos = fetch_user_logos(st.session_state.user_email)
    for logo in logos:
        st.image(logo["file_url"], caption=f"{logo['title']} - {logo['description']}")

# Main Application
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "firebase_initialized" not in st.session_state:
    initialize_firebase()

if st.session_state.logged_in:
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Generate Logo"])
    st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"logged_in": False}))

    if page == "Home":
        user_home_page()
    elif page == "Generate Logo":
        logo_generation_page()
else:
    st.sidebar.title("Authentication")
    auth_option = st.sidebar.radio("Choose an option", ["Login", "Sign Up"])
    
    if auth_option == "Login":
        login_page()
    elif auth_option == "Sign Up":
        signup_page()
