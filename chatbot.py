import requests
import json
import os
import time
from datetime import datetime
import pandas as pd
import numpy as np

# API configuration
API_KEY = "OPENROUTER_API_KEY"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Distance calculation between two geographic coordinates
def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate the distance between two geographic coordinates in kilometers"""
    from math import sin, cos, sqrt, atan2, radians
    
    # Approximate radius of earth in km
    R = 6371.0
    
    lat1, lon1 = radians(lat1), radians(lon1)
    lat2, lon2 = radians(lat2), radians(lon2)
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    distance = R * c
    return distance

def find_nearby_heritage_places(user_lat, user_lon, max_distance=50):
    """Find heritage places near the user's location"""
    try:
        # Load the dataset
        CSV_FILE = "dataset/combined_tourist_data.csv"
        df = pd.read_csv(CSV_FILE, encoding="ISO-8859-1", on_bad_lines="skip")
        
        # If dataset has no coordinates, use Tamil Nadu tourist places dataset
        if 'Latitude' not in df.columns or 'Longitude' not in df.columns:
            CSV_FILE = "dataset/tamilnadu_tourist_places_with_description.csv"
            df = pd.read_csv(CSV_FILE, encoding="ISO-8859-1", on_bad_lines="skip")
        
        nearby_places = []
        
        # Check if dataset has coordinates
        if 'Latitude' in df.columns and 'Longitude' in df.columns:
            # Filter places with valid coordinates
            for _, row in df.iterrows():
                if pd.notna(row.get('Latitude')) and pd.notna(row.get('Longitude')):
                    try:
                        place_lat = float(row['Latitude'])
                        place_lon = float(row['Longitude'])
                        
                        # Calculate distance
                        distance = calculate_distance(user_lat, user_lon, place_lat, place_lon)
                        
                        if distance <= max_distance:
                            nearby_places.append({
                                'name': row['Place Name'],
                                'distance': round(distance, 2),
                                'description': row.get('Description', 'No description available')[:100] + '...'
                            })
                    except (ValueError, TypeError):
                        continue
        
        # If no places with coordinates found, fallback to general places
        if not nearby_places:
            # Get a sample of places as fallback
            for _, row in df.iloc[:5].iterrows():
                nearby_places.append({
                    'name': row['Place Name'],
                    'description': row.get('Description', 'No description available')[:100] + '...'
                })
        
        # Sort by distance if available
        if nearby_places and 'distance' in nearby_places[0]:
            nearby_places = sorted(nearby_places, key=lambda x: x['distance'])
        
        return nearby_places[:5]  # Return top 5 places
    except Exception as e:
        print(f"Error finding nearby places: {e}")
        return []

def get_location_name(lat, lon):
    """Get location name from coordinates using OpenStreetMap Nominatim API with better error handling"""
    try:
        # Add user agent and timeout to improve reliability
        headers = {
            'User-Agent': 'TamilNaduHeritageGuide/1.0',
        }
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=14"
        response = requests.get(url, headers=headers, timeout=5)
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            
            if 'address' in data:
                address = data['address']
                # Extract location components with more fallback options
                locality = (address.get('suburb') or 
                          address.get('neighbourhood') or 
                          address.get('village') or 
                          address.get('hamlet') or
                          address.get('town') or 
                          address.get('city') or 
                          address.get('municipality') or
                          "")
                
                district = (address.get('county') or 
                          address.get('state_district') or
                          address.get('district') or
                          "Salem")
                
                state = address.get('state') or "Tamil Nadu"
                country = address.get('country') or "India"
                
                # If we have a location name in display_name, use it as a backup
                if not locality and 'display_name' in data:
                    parts = data['display_name'].split(',')
                    if len(parts) > 0:
                        locality = parts[0].strip()
                
                # Use a hardcoded table of known coordinates for major places in Tamil Nadu
                # This serves as a fallback when the API doesn't return good results
                known_locations = {
                    # Format: "latitude_longitude": "location_name"
                    "11.671253_78.162144": "Salem",
                    "13.0827_80.2707": "Chennai",
                    "11.0168_76.9558": "Coimbatore",
                    "9.9252_78.1198": "Madurai",
                    "10.7905_78.7047": "Tiruchirappalli",
                    "12.9716_79.1946": "Vellore",
                    # Add more known locations as needed
                }
                
                # Create a key by rounding coordinates to 4 decimal places for fuzzy matching
                key = f"{round(lat, 4)}_{round(lon, 4)}"
                
                # If we still don't have a locality but have coordinates in our known locations
                if not locality:
                    for known_key, known_name in known_locations.items():
                        known_lat, known_lon = map(float, known_key.split('_'))
                        # Check if coordinates are close (within ~5km)
                        if abs(lat - known_lat) < 0.05 and abs(lon - known_lon) < 0.05:
                            locality = known_name
                            break
                
                if locality:
                    location_text = f"{locality}, {district}, {state}, {country}".strip()
                    return location_text
                else:
                    # As a last resort, use district name
                    return f"{district}, {state}, {country}"
            
            # If the JSON doesn't have the expected structure
            elif 'error' in data:
                print(f"Nominatim API error: {data['error']}")
            
            # Use hardcoded location data based on coordinates
            return get_hardcoded_location(lat, lon)
        
        else:
            print(f"Nominatim API request failed with status code: {response.status_code}")
            return get_hardcoded_location(lat, lon)
            
    except Exception as e:
        print(f"Error fetching location name: {e}")
        return get_hardcoded_location(lat, lon)

def get_hardcoded_location(lat, lon):
    """Fallback to determine location based on coordinates when API fails"""
    # Define regions of Tamil Nadu based on coordinates
    if 11.65 <= lat <= 11.69 and 78.15 <= lon <= 78.18:
        return "Salem, Tamil Nadu, India"
    elif 13.07 <= lat <= 13.09 and 80.26 <= lon <= 80.28:
        return "Chennai, Tamil Nadu, India"
    elif 9.92 <= lat <= 9.94 and 78.11 <= lon <= 78.13:
        return "Madurai, Tamil Nadu, India"
    elif 10.78 <= lat <= 10.80 and 78.69 <= lon <= 78.71:
        return "Tiruchirappalli, Tamil Nadu, India"
    elif 11.01 <= lat <= 11.03 and 76.95 <= lon <= 76.97:
        return "Coimbatore, Tamil Nadu, India"
    # For the specific coordinates in the report
    elif 11.67 <= lat <= 11.68 and 78.16 <= lon <= 78.17:
        return "Salem, Tamil Nadu, India"
    # Default fallback
    else:
        # Calculate nearest major city in Tamil Nadu by using a simple lookup
        major_cities = [
            {"name": "Salem", "lat": 11.6712, "lon": 78.1621},
            {"name": "Chennai", "lat": 13.0827, "lon": 80.2707},
            {"name": "Madurai", "lat": 9.9252, "lon": 78.1198},
            {"name": "Coimbatore", "lat": 11.0168, "lon": 76.9558},
            {"name": "Tiruchirappalli", "lat": 10.7905, "lon": 78.7047},
            {"name": "Vellore", "lat": 12.9716, "lon": 79.1946}
        ]
        
        closest_city = None
        closest_distance = float('inf')
        
        for city in major_cities:
            dist = calculate_distance(lat, lon, city["lat"], city["lon"])
            if dist < closest_distance:
                closest_distance = dist
                closest_city = city["name"]
        
        return f"{closest_city}, Tamil Nadu, India"

def get_chatbot_response(user_message, history=None, user_location=None):
    """
    Get a response from the chatbot API using OpenRouter
    
    Args:
        user_message (str): The user's message to the chatbot
        history (list, optional): Chat history for context
        user_location (dict, optional): User's location data with lat and lon
    
    Returns:
        str: The chatbot's response
    """
    if history is None:
        history = []
    
    # Check if the message is asking about current location
    location_question_keywords = [
        "where am i", "my location", "current location", "where i am", 
        "my current location", "what is my location", "tell me my location", 
        "give me my location", "what's my location", "show my location"
    ]
    
    # Expanded keywords for nearby heritage places search
    nearby_keywords = [
        "nearby", "near me", "close by", "around here", "in this area", 
        "proximity", "local", "surrounding", "in my area", "nearest"
    ]
    
    heritage_keywords = [
        "heritage", "monuments", "temples", "historical", "tourist", 
        "places", "sites", "attractions", "landmarks", "visit", 
        "sightseeing", "tourism", "famous", "spots", "destinations", 
        "buildings", "architecture"
    ]
    
    # Check if the user is asking about their current location
    is_asking_location = any(keyword in user_message.lower() for keyword in location_question_keywords)
    
    if is_asking_location and user_location and 'lat' in user_location and 'lon' in user_location:
        location_name = get_location_name(user_location['lat'], user_location['lon'])
        if "Unknown location" in location_name:
            # If we still get Unknown location, use the fallback with coordinates
            location_name = get_hardcoded_location(user_location['lat'], user_location['lon'])
            
        return f"Based on your coordinates, your current location is: {location_name}. You are at latitude {user_location['lat']:.6f} and longitude {user_location['lon']:.6f}."
    
    # Check if the message is asking about nearby places - improved detection
    is_asking_nearby = any(keyword in user_message.lower() for keyword in nearby_keywords)
    is_asking_heritage = any(keyword in user_message.lower() for keyword in heritage_keywords)
    
    # Special case for direct "nearby heritage places" question
    if "nearby heritage places" in user_message.lower() or "near heritage places" in user_message.lower():
        is_asking_nearby = True
        is_asking_heritage = True
    
    # If user is asking about nearby heritage places and we have location data
    if is_asking_nearby and is_asking_heritage and user_location and 'lat' in user_location and 'lon' in user_location:
        try:
            location_name = get_location_name(user_location['lat'], user_location['lon'])
            nearby_places = find_nearby_heritage_places(user_location['lat'], user_location['lon'])
            
            if nearby_places:
                response = f"Based on your current location in {location_name}, here are some nearby heritage places you might want to visit:\n\n"
                
                for i, place in enumerate(nearby_places, 1):
                    response += f"{i}. **{place['name']}**"
                    if 'distance' in place:
                        response += f" ({place['distance']} km away)"
                    response += f"\n   {place['description']}\n\n"
                
                response += "Would you like more details about any of these places? Just ask about one that interests you."
                return response
            else:
                return f"I couldn't find any heritage places near your current location ({location_name}). Would you like me to suggest some popular heritage sites in Tamil Nadu instead?"
        except Exception as e:
            print(f"Error processing nearby places: {e}")
    
    # If not asking for nearby places or there was an error, proceed with normal AI response
    # Prepare the message format
    messages = [
        {"role": "system", "content": "You are a helpful Tamil Nadu heritage tourism guide. Provide concise, informative responses about Tamil Nadu's cultural sites, temples, history, and tourist information. Keep responses under 150 words."}
    ]
    
    # Add history for context
    for msg in history[-5:]:  # Keep last 5 messages for context
        messages.append(msg)
    
    # Add the user's current message
    messages.append({"role": "user", "content": user_message})
    
    # Try a simpler approach with just one model that's known to work well
    try:
        print(f"Processing message: {user_message}")
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://tamilnadu-heritage-guide.com",
            "X-Title": "Tamil Nadu Heritage Guide"
        }
        
        data = {
            "model": "mistralai/mistral-7b-instruct:free",  # Use a model that's definitely available on OpenRouter
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 300
        }
        
        # Make API request
        print(f"Sending request to OpenRouter API...")
        response = requests.post(API_URL, headers=headers, json=data, timeout=30)
        print(f"API Status: {response.status_code}")
        
        # Print the response for debugging
        if response.status_code != 200:
            print(f"Error response: {response.text}")
            # Return a fallback response with helpful info
            return "I'm sorry, I couldn't connect to my knowledge base. Tamil Nadu is known for its magnificent temples like Meenakshi Amman Temple in Madurai and Brihadeeswara Temple in Thanjavur. The state has a rich cultural heritage with classical dance forms like Bharatanatyam and beautiful hill stations like Ooty and Kodaikanal."
        
        # Parse response
        result = response.json()
        print(f"Received response: {json.dumps(result)[:200]}...")
        
        if 'choices' in result and len(result['choices']) > 0:
            bot_response = result['choices'][0]['message']['content']
            return bot_response
        else:
            print(f"API returned unexpected format: {json.dumps(result)}")
            return "I'm sorry, I received an unexpected response format. Tamil Nadu is famous for its magnificent temples, many of which are UNESCO World Heritage sites like the Brihadeeswara Temple in Thanjavur."
    
    except Exception as e:
        print(f"Error in chatbot: {str(e)}")
        return "I'm sorry, I encountered an error while processing your request. Tamil Nadu has a rich cultural history dating back thousands of years, with notable dynasties including the Cholas, Pandyas, and Pallavas."

def log_conversation(user_message, bot_response):
    """Log conversation for analysis"""
    try:
        os.makedirs('logs', exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp}\nUser: {user_message}\nBot: {bot_response}\n\n"
        
        with open('logs/chatbot_conversations.log', 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Logging error: {e}")
