from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
import os
import requests
from deep_translator import GoogleTranslator  # Import translation library
from urllib.parse import unquote
import re
import numpy as np  # Import NumPy to handle NaN values
from chatbot import get_chatbot_response, log_conversation
from datetime import datetime  # Add this import at the top of the file

app = Flask(__name__, static_folder='static')

# Load the dataset
CSV_FILE = "dataset/salem_tourist_places_cleaned.csv"
df = pd.read_csv(CSV_FILE, encoding="ISO-8859-1", on_bad_lines="skip")


# Image directory (update based on your system)
IMAGE_DIR = r"D:/tamilnadu_heritage/images"

ORS_API_KEY = "OPENROUTER_API_KEY"  # Your OpenRouteService API Key

def get_nearby_places(user_lat, user_lon, max_distance_km=50):
    nearby_places = []
    user_coords = [user_lon, user_lat]  # OpenRouteService requires [longitude, latitude]

    print("\n📌 Starting Nearby Places Search...")
    print(f"📍 User Location: {user_lat}, {user_lon}\n")

    for _, row in df.iterrows():
        try:
            place_lat = float(row["Latitude"])
            place_lon = float(row["Longitude"])
            place_coords = [place_lon, place_lat]

            # Use OpenRouteService API to get driving distance
            url = "https://api.openrouteservice.org/v2/directions/driving-car"
            headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
            payload = {
                "coordinates": [user_coords, place_coords],  # Correct order
                "format": "json"
            }

            response = requests.post(url, headers=headers, json=payload)
            response_json = response.json()

            if "routes" in response_json and len(response_json["routes"]) > 0:
                distance_meters = response_json["routes"][0]["summary"]["distance"]
                distance_km = round(distance_meters / 1000, 2)  # Convert meters to km

                # Ensure filtering is correct
                if distance_km <= max_distance_km + 15:  # Buffer increased to 15 km
                    nearby_places.append({
                        "name": row["Place Name"],
                        "short_description": row.get("Short Description", row.get("Description", "")),
                        "distance_km": distance_km,
                        "image": row["Sub-Place Images"].split(", ")[0] if pd.notna(row["Sub-Place Images"]) else "default.jpg"
                    })

        except (ValueError, TypeError) as e:
            print(f"⚠️ Skipping {row['Place Name']} due to error: {e}")
            continue  # Skip invalid values

    return sorted(nearby_places, key=lambda x: x["distance_km"])  # Sort by closest places first

# Function to translate text
def translate_text(text, target_lang):
    return GoogleTranslator(source='auto', target=target_lang).translate(text)

@app.route("/")
def home():
    return render_template("index.html", places=df.to_dict(orient="records"))

# Load tour packages data
def load_tour_packages():
    regular_tours_file = "dataset/conducted_tour_packages_by_tamilnadu_tourism_development_corporation_limited_2008-09_2010.csv"
    seasonal_tours_file = "dataset/conducted_tour_packages_by_tamilnadu_tourism_development_corporation_limited_2008-09_tours_2010.csv"
    
    try:
        regular_df = pd.read_csv(regular_tours_file, encoding="ISO-8859-1", on_bad_lines="skip")
        seasonal_df = pd.read_csv(seasonal_tours_file, encoding="ISO-8859-1", on_bad_lines="skip")
        
        regular_tours = []
        optional_tours = []
        
        for _, row in regular_df.iterrows():
            tour_type = row.get('Tours', '')
            tour_data = {
                'name': row.get('Name of the Tour Regular Tours', ''),
                'time': row.get('Time and Places Covered', ''),
                'category': tour_type
            }
            
            if 'Regular Tours' in tour_type:
                regular_tours.append(tour_data)
            elif 'Optional Tours' in tour_type:
                optional_tours.append(tour_data)
        
        seasonal_tours = []
        ltc_tours = []
        rail_tours = []
        
        for _, row in seasonal_df.iterrows():
            tour_type = row.get('Description', '')
            tour_data = {
                'name': row.get('Tour', ''),
                'category': tour_type
            }
            
            if 'Seasonal Special Tours' in tour_type:
                seasonal_tours.append(tour_data)
            elif 'Leave Travel Concession Tours' in tour_type:
                ltc_tours.append(tour_data)
            elif 'Rail Cum Road Tour' in tour_type:
                rail_tours.append(tour_data)
        
        return {
            'regular_tours': regular_tours,
            'optional_tours': optional_tours,
            'seasonal_tours': seasonal_tours,
            'ltc_tours': ltc_tours,
            'rail_tours': rail_tours
        }
    except Exception as e:
        print(f"Error loading tour packages: {e}")
        return {
            'regular_tours': [],
            'optional_tours': [],
            'seasonal_tours': [],
            'ltc_tours': [],
            'rail_tours': []
        }

@app.route("/explore")
def explore():
    # Get tour packages data
    tour_packages = load_tour_packages()
    
    # Load heritage places data
    places = df.to_dict(orient="records")
    
    # Pass all data to the template
    return render_template(
        "explore.html", 
        places=places,
        regular_tours=tour_packages['regular_tours'],
        optional_tours=tour_packages['optional_tours'],
        seasonal_tours=tour_packages['seasonal_tours'],
        ltc_tours=tour_packages['ltc_tours'],
        rail_tours=tour_packages['rail_tours']
    )

def clean_description(description):
    """Cleans and formats the description text properly with bullet points and bold headers."""
    if not isinstance(description, str) or not description.strip():
        return "No description available."

    # Fix newline issues for proper HTML formatting
    description = description.replace("\n", "<br>")

    # Fix encoding issues
    replacements = {
        "": "-",  # Fix en-dash issues
        "â€“": "-",  # Another en-dash issue
        "â€”": "—",  # Fix em-dash
        "â€™": "’",  # Fix apostrophe (e.g., Lady’s)
        "â€˜": "‘",  # Left single quote
        "â€œ": "“",  # Left double quote
        "â€": "”",  # Right double quote
        "â€¦": "...",  # Fix ellipsis
        "Â": "",  # Remove unwanted Â characters
        "": "’",  # Additional fix for apostrophes
    }

    for wrong, correct in replacements.items():
        description = description.replace(wrong, correct)

    # Ensure bullet points are properly formatted
    description = re.sub(r"(<br>\s*)?-+\s", "<ul><li>", description, 1)  # First bullet starts <ul>
    description = re.sub(r"<br>\s*-+\s", "<br><li>", description)  # Remaining bullets as <li>
    description = description.replace("<br><li>", "</li><br><li>")  # Close <li> before adding another
    description = description.replace("</li><br>", "</li>")  # Remove unnecessary <br>

    if "<ul><li>" in description:
        description += "</li></ul>"  # Ensure list closes properly

    # Convert section titles (e.g., "Why Visit:") into bold
    description = re.sub(r"(?<=<br>)([A-Za-z0-9\s&]+):", r"<br><strong>\1:</strong>", description)

    return description


@app.route("/place/<place_name>")
def place_details(place_name):
    place_name = unquote(place_name).replace("_", " ")  # Fix URL decoding
    place_name = place_name.lower().strip()  # Normalize input for case-insensitive search

    # Normalize dataset values for matching
    df["Place Name Normalized"] = df["Place Name"].str.lower().str.strip()

    # Search for the place in the dataset
    place = df[df["Place Name Normalized"] == place_name].to_dict(orient="records")

    if place:
        place_data = place[0]

        if "Description" in place_data:
            place_data["Description"] = clean_description(place_data["Description"])

        # ✅ Process Image Paths (Remove Extra Characters)
        if "Sub-Place Images" in place_data and isinstance(place_data["Sub-Place Images"], str):
            all_images = [
                img.strip().replace("'", "").replace("[", "").replace("]", "")
                for img in place_data["Sub-Place Images"].split(", ")
                if img.strip()
            ]
        else:
            all_images = []

        # ✅ Assign Main Images (Ensure 3 Images)
        main_images = all_images[:3] if len(all_images) >= 3 else all_images + ["default.jpg"] * (3 - len(all_images))

        # ✅ Process Sub-Places (Only if they exist and are not empty)
        sub_places = []
        sub_descriptions = []
        sub_place_images = []

        # Check if Sub-Places exists and is not empty
        if "Sub-Places" in place_data and isinstance(place_data["Sub-Places"], str) and place_data["Sub-Places"].strip():
            sub_places = [sp.strip() for sp in place_data["Sub-Places"].split(",") if sp.strip() and sp != "[]"]

        # Process Sub-Place Descriptions (Only if they exist)
        if "Sub-Place Descriptions" in place_data and isinstance(place_data["Sub-Place Descriptions"], str) and place_data["Sub-Place Descriptions"].strip():
            sub_descriptions = [desc.strip() for desc in place_data["Sub-Place Descriptions"].split("|||") if desc.strip() and desc != "[]"]

        # Process Sub-Place Images (skip the main images)
        sub_place_images = all_images[3:] if len(all_images) > 3 else []

        # ✅ Ensure Sub-Places Have Correct Image & Description
        sub_place_data = []
        if sub_places:  # Only add sub-places if they exist and are valid
            for i in range(len(sub_places)):
                sub_place_data.append({
                    "name": sub_places[i],
                    "image": sub_place_images[i] if i < len(sub_place_images) else None,
                    "description": sub_descriptions[i] if i < len(sub_descriptions) else "No description available."
                })

        # ✅ Update place_data with structured data
        place_data["Main Images"] = main_images

        # ✅ Only Include Sub-Places Data if Not Empty or Invalid
        if sub_place_data:  # Only add this key if there are valid sub-places
            place_data["Sub-Places Data"] = sub_place_data

        # Print the sub-places data for debugging
        print("Sub-Places Data:", place_data.get("Sub-Places Data", "No Sub-Places"))

        # Render the template with place data (sub-places data will be included only if they exist)
        return render_template("place.html", place=place_data)

    else:
        # If the place is not found, return an error page
        return render_template("error.html", message="Place not found"), 404


@app.route("/nearby", methods=["POST"])
def nearby():
    data = request.json
    user_lat = data.get("latitude")
    user_lon = data.get("longitude")

    if user_lat and user_lon:
        try:
            places = get_nearby_places(float(user_lat), float(user_lon))
            return jsonify(places)
        except ValueError:
            return jsonify({"error": "Invalid coordinates"})

    return jsonify({"error": "Coordinates missing"})

@app.route("/translate", methods=["POST"])
def translate():
    data = request.json
    text = data.get("text")
    target_lang = data.get("language")
    is_batch = data.get("batch", False)

    if not text or not target_lang:
        return jsonify({"error": "Invalid input"})

    try:
        if is_batch:
            # Handle batch translation
            texts = text.split('\n|||\n')
            translated_texts = []
            
            for item in texts:
                if item.strip():
                    translated = GoogleTranslator(source='auto', target=target_lang).translate(item)
                    translated_texts.append(translated)
                else:
                    translated_texts.append("")
            
            return jsonify({"translated_texts": translated_texts})
        else:
            # Handle single text translation
            translated_text = GoogleTranslator(source='auto', target=target_lang).translate(text)
            return jsonify({"translated_text": translated_text})
    
    except Exception as e:
        print(f"Translation error: {e}")
        return jsonify({"error": f"Translation failed: {str(e)}"})

@app.route("/chatbot", methods=["POST"])
def chatbot_endpoint():
    try:
        data = request.json
        if not data:
            print("No JSON data received")
            return jsonify({"error": "No data provided", "response": "I couldn't understand your message."}), 400
        
        user_message = data.get("message", "")
        chat_history = data.get("history", [])
        user_location = data.get("location")  # Get user location if provided
        
        if not user_message:
            print("No message provided")
            return jsonify({"error": "No message provided", "response": "Please provide a message."}), 400
        
        print(f"Received message: {user_message}")
        if user_location:
            print(f"User location: {user_location}")
        
        # Get response from chatbot
        bot_response = get_chatbot_response(user_message, chat_history, user_location)
        
        # Log the conversation
        log_conversation(user_message, bot_response)
        
        # Return the response with current time
        current_time = datetime.now().strftime("%H:%M")
        print(f"Sending response: {bot_response[:50]}...")
        
        return jsonify({
            "response": bot_response,
            "timestamp": current_time
        })
    except Exception as e:
        print(f"Error in chatbot endpoint: {str(e)}")
        return jsonify({
            "response": "I apologize, but I'm having technical difficulties right now. Please try again later.",
            "timestamp": datetime.now().strftime("%H:%M")
        })

@app.route("/images/IMAGE_UPDATED/<filename>")
def serve_updated_image(filename):
    image_folder = r"D:/tamilnadu_heritage/IMAGE_UPDATED"
    return send_from_directory(image_folder, filename)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

if __name__ == "__main__":
    app.run(debug=True)
