import tkinter as tk
from tkinter import messagebox, PhotoImage
import tkintermapview
import requests
import asyncio
import aiohttp
import json
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from datetime import datetime
from PIL import Image, ImageTk  # You'll need to pip install pillow

# Add these color constants at the top
AI_DARK = "#1A1A2E"  # Dark background
AI_ACCENT = "#0F3460"  # Secondary background
AI_HIGHLIGHT = "#16213E"  # Highlight color
AI_GLOW = "#00FFB3"  # Neon glow color
AI_TEXT = "#E9E9E9"  # Text color

# OpenWeatherMap API Key
API_KEY = "bfce929e6f2f0856b2b6761bad1f0cae"
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

# Caching dictionary for previously searched locations
location_cache = {}

# Function to fetch weather data asynchronously
async def fetch_weather(session, lat, lon):
    url = f"{BASE_URL}?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    try:
        async with session.get(url) as response:
            if response.status == 429:  # Rate limit exceeded
                messagebox.showerror("Error", "API rate limit exceeded. Please try again later.")
                return {"error": "Rate limit exceeded"}
            elif response.status != 200:
                messagebox.showerror("Error", f"API Error: Status {response.status}")
                return {"error": f"API Status: {response.status}"}
            
            return await response.json()
    except aiohttp.ClientError as e:
        return {"error": f"Connection error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}

# Function to fetch and display weather data
async def get_weather(lat, lon):
    async with aiohttp.ClientSession() as session:
        data = await fetch_weather(session, lat, lon)
    
    if "error" in data:
        messagebox.showerror("Error", f"Failed to get data: {data['error']}")
        return
    
    try:
        temp = data["main"]["temp"]
        weather_desc = data["weather"][0]["description"].capitalize()
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        
        # Get weather recommendations
        recommendations = get_weather_recommendations(data)
        
        result_label.config(text=f"🌡 Temperature: {temp}°C\n"
                               f"☁ Condition: {weather_desc}\n"
                               f"💧 Humidity: {humidity}%\n"
                               f"🌬 Wind Speed: {wind_speed} m/s\n\n"
                               f"📌 Recommendations:\n{recommendations}", fg="white")
        
    except KeyError:
        messagebox.showerror("Error", "Invalid response from API")

# Function to search for a city and update the map
async def search():
    city = city_entry.get().strip()
    if not city:
        messagebox.showerror("Error", "Please enter a city name")
        return
    
    if city in location_cache:
        lat, lon = location_cache[city]
    else:
        # Enhanced search URL with more precise parameters
        url = f"https://nominatim.openstreetmap.org/search"
        params = {
            "q": city,
            "format": "json",
            "addressdetails": 1,
            "limit": 10,  # Increased number of results
            "accept-language": "en",
            "featuretype": ["city", "town", "village", "suburb", "neighbourhood"],  # Added more location types
            "namedetails": 1,
            "extratags": 1,
            "dedupe": 1,
            "bounded": 1,
            "polygon_geojson": 1,  # Get boundary data
            "countrycodes": "",    # Can be set for specific country
            "viewbox": "-180,90,180,-90",  # World viewbox
            "bounded": 1
        }
        headers = {
            "User-Agent": "WeatherMapApp/3.0",
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, headers=headers) as response:
                    data = await response.json()
                    if data:
                        # Enhanced location matching algorithm
                        best_match = None
                        highest_score = 0
                        
                        for location in data:
                            score = 0
                            # Score based on type
                            if location.get('type') == 'city':
                                score += 5
                            elif location.get('type') == 'town':
                                score += 4
                            elif location.get('type') == 'village':
                                score += 3
                            
                            # Score based on importance (if available)
                            if 'importance' in location:
                                score += float(location['importance']) * 2
                                
                            # Score based on name match
                            if location.get('name', '').lower() == city.lower():
                                score += 3
                            
                            # Check for exact matches in address details
                            if 'address' in location:
                                if city.lower() in [
                                    location['address'].get('city', '').lower(),
                                    location['address'].get('town', '').lower(),
                                    location['address'].get('village', '').lower()
                                ]:
                                    score += 4
                            
                            if score > highest_score:
                                highest_score = score
                                best_match = location
                        
                        # Replace the existing zoom_level dictionary with a fixed zoom level of 10
                        zoom_level = 10  # Fixed zoom level for all searches
                        
                        if best_match:
                            lat = float(best_match['lat'])
                            lon = float(best_match['lon'])
                            location_cache[city] = (round(lat, 8), round(lon, 8))
                            
                            # Enhanced location display
                            address = best_match.get('address', {})
                            city_name = address.get('city') or address.get('town') or address.get('village') or best_match.get('name')
                            state = address.get('state', '')
                            country = address.get('country', '')
                            
                            location_info = f"📍 {city_name}\n"
                            if state:
                                location_info += f"🏛️ {state}\n"
                            if country:
                                location_info += f"🌎 {country}"
                            
                            result_label.config(text=location_info, fg="white")
                        else:
                            messagebox.showerror("Error", "City not found. Please try with a more specific name.")
                            return
                    else:
                        messagebox.showerror("Error", "Location not found. Please try with a more specific name.")
                        return
            except Exception as e:
                messagebox.showerror("Error", f"Search error: {str(e)}")
                return

    # Update map with the fixed zoom level
    map_widget.delete_all_marker()
    map_widget.set_position(lat, lon)
    map_widget.set_zoom(13)  # Changed from 10 to 13

    # Fetch weather data
    await get_weather(lat, lon)

# Function to get weather on map click
def on_map_click(marker):
    lat, lon = marker.position
    asyncio.run(get_weather(lat, lon))

# Function to switch map modes
def set_map_mode(mode):
    map_widget.set_tile_server(mode)

# Function to handle Enter key press
def on_enter(event):
    asyncio.run(search())

# Add this function for weather recommendations
def get_weather_recommendations(weather_data):
    temp = weather_data['main']['temp']
    weather = weather_data['weather'][0]['description'].lower()
    wind_speed = weather_data['wind']['speed']
    humidity = weather_data['main']['humidity']
    
    recommendations = []

    # Temperature based advice
    if temp < 0:
        recommendations.append("❄️ Extreme cold - Wear heavy winter clothing and layers")
    elif temp < 10:
        recommendations.append("❄️ Cold weather - Wear warm clothes, layers recommended")
    elif temp < 15:
        recommendations.append("🧥 Cool weather - Light jacket or sweater recommended")
    elif temp < 20:
        recommendations.append("🧥 Mild weather - Light jacket or sweater weather")
    elif temp < 25:
        recommendations.append("👕 Pleasant weather - Perfect for light clothing")
    elif temp < 30:
        recommendations.append("☀️ Warm weather - Light, breathable clothing recommended")
    else:
        recommendations.append("🌞 Hot weather - Stay hydrated, wear light & breathable clothes")
    
    # Weather condition based advice
    if "rain" in weather:
        recommendations.append("☔ Don't forget your umbrella!")
        recommendations.append("👢 Waterproof footwear recommended")
    elif "thunderstorm" in weather:
        recommendations.append("⛈️ Stay indoors during thunderstorms")
        recommendations.append("🔌 Unplug electronic devices")
    elif "cloud" in weather:
        recommendations.append("🌥️ Good for outdoor activities")
        recommendations.append("🕶️ UV protection still needed")
    elif "clear" in weather:
        recommendations.append("😎 Great day for outdoor activities!")
        recommendations.append("🧴 Don't forget sunscreen")
    elif "snow" in weather:
        recommendations.append("⛄ Wear waterproof boots and gloves")
        recommendations.append("🧤 Keep extremities warm")
    
    # Humidity based advice
    if humidity > 80:
        recommendations.append("💧 High humidity - Stay hydrated and avoid strenuous activities")
    elif humidity < 30:
        recommendations.append("🌵 Low humidity - Use moisturizer and stay hydrated")
    
    # Wind based advice
    if wind_speed > 20:
        recommendations.append("💨 Strong winds - Secure loose items and be careful outdoors")
    elif wind_speed > 10:
        recommendations.append("💨 Windy conditions - Secure loose items")
    
    # UV Index based advice (if available)
    if 'uvi' in weather_data:
        uvi = weather_data['uvi']
        if uvi > 10:
            recommendations.append("⚠️ Extreme UV - Minimize sun exposure")
        elif uvi > 7:
            recommendations.append("☀️ High UV - Use sunscreen and seek shade")
        elif uvi > 3:
            recommendations.append("🌤️ Moderate UV - Use sunscreen")
    
    return "\n".join(recommendations)

# Add weather history tracking
weather_history = []

def update_weather_history(temp):
    global weather_history
    weather_history.append(temp)
    if len(weather_history) > 10:
        weather_history.pop(0)
    update_temperature_graph()

def update_temperature_graph():
    for widget in graph_frame.winfo_children():
        widget.destroy()
    
    if len(weather_history) > 1:
        dims = calculate_responsive_dimensions(root)
        fig_width = dims['map_width'] / 100
        fig_height = dims['map_height'] / 200
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        ax.plot(weather_history, marker='o')
        ax.set_title('Temperature History', 
                    fontsize=dims['normal_font_size'])
        ax.set_ylabel('Temperature (°C)', 
                     fontsize=dims['normal_font_size'])
        plt.xticks(fontsize=dims['normal_font_size']-2)
        plt.yticks(fontsize=dims['normal_font_size']-2)
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# Update the calculate_responsive_dimensions function
def calculate_responsive_dimensions(root):
    # Get screen width and height
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Base scale factor on screen resolution
    scale_factor = min(screen_width/1920, screen_height/1080)
    
    return {
        'scale': scale_factor,
        'window_width': int(screen_width * 0.9),
        'window_height': int(screen_height * 0.9),
        'header_font_size': int(24 * scale_factor),
        'normal_font_size': int(12 * scale_factor),
        'button_font_size': int(11 * scale_factor),
        'padding': int(10 * scale_factor),
        'entry_width': int(40 * scale_factor)
    }

# Create a responsive container frame
def create_responsive_layout(root, dims):
    # Main container
    main_container = tk.Frame(root, bg=AI_DARK)
    main_container.pack(fill=tk.BOTH, expand=True, padx=dims['padding'], pady=dims['padding'])
    
    # Header section (10% of height)
    header_frame = tk.Frame(main_container, bg=AI_ACCENT)
    header_frame.pack(fill=tk.X, pady=(0, dims['padding']))
    
    # Search section (10% of height)
    search_frame = tk.Frame(main_container, bg=AI_ACCENT)
    search_frame.pack(fill=tk.X, pady=dims['padding'])
    
    # Map section (50% of height)
    map_container = tk.Frame(main_container, bg=AI_DARK)
    map_container.pack(fill=tk.BOTH, expand=True, pady=dims['padding'])
    
    # Results section (15% of height)
    results_frame = tk.Frame(main_container, bg=AI_DARK)
    results_frame.pack(fill=tk.X, pady=dims['padding'])
    
    # Controls section (15% of height)
    controls_frame = tk.Frame(main_container, bg=AI_DARK)
    controls_frame.pack(fill=tk.X, pady=dims['padding'])
    
    return (header_frame, search_frame, map_container, results_frame, controls_frame)

# Update the window resize handler
def on_window_resize(event=None):
    if event and event.widget != root:
        return
        
    dims = calculate_responsive_dimensions(root)
    
    # Update all font sizes and dimensions
    header_label.configure(
        font=("Helvetica", dims['header_font_size'], "bold")
    )
    
    # Update search entry
    city_entry.configure(
        font=("Helvetica", dims['normal_font_size']),
        width=dims['entry_width']
    )
    
    # Update all buttons
    for button in [search_button, temp_button, pressure_button] + map_mode_buttons:
        button.configure(
            font=("Helvetica", dims['button_font_size'], "bold"),
            padx=dims['padding'],
            pady=dims['padding']//2
        )
    
    # Update map size
    map_height = int(dims['window_height'] * 0.5)
    map_width = int(dims['window_width'] * 0.9)
    map_widget.set_size(map_width, map_height)
    
    # Update result label
    result_label.configure(
        font=("Helvetica", dims['normal_font_size']),
        wraplength=dims['window_width'] * 0.8
    )
    
    # Update graph if exists
    if len(weather_history) > 1:
        update_temperature_graph()

# Create main window
root = tk.Tk()
dims = calculate_responsive_dimensions(root)
root.configure(bg=AI_DARK)
root.title("AI Weather & Map Analysis")

# Make window responsive
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)
root.geometry(f"{dims['window_width']}x{dims['window_height']}")
root.resizable(True, True)

# Create responsive layout
header_frame, search_frame, map_container, results_frame, controls_frame = create_responsive_layout(root, dims)

# Create header with responsive font
header_label = tk.Label(
    header_frame,
    text="AI Weather & Map Analysis System",
    font=("Helvetica", dims['header_font_size'], "bold"),
    bg=AI_ACCENT,
    fg=AI_GLOW
)
header_label.pack(fill=tk.X, pady=dims['padding'])

# Create search entry with responsive size
search_container = tk.Frame(search_frame, bg=AI_ACCENT)
search_container.pack(expand=True, fill=tk.X, padx=dims['padding'], pady=dims['padding'])

# Create a frame for the search entry and buttons
search_content = tk.Frame(search_container, bg=AI_ACCENT)
search_content.pack(expand=True)

city_entry = tk.Entry(
    search_content,
    font=("Helvetica", dims['normal_font_size']),
    width=dims['entry_width'],
    bg=AI_HIGHLIGHT,
    fg=AI_TEXT,
    insertbackground=AI_GLOW
)
city_entry.pack(side=tk.LEFT, padx=5)
city_entry.bind("<Return>", on_enter)  # Bind Enter key to search

# Create responsive buttons
button_style = {
    "font": ("Helvetica", dims['button_font_size'], "bold"),
    "bg": AI_HIGHLIGHT,
    "fg": AI_GLOW,
    "activebackground": AI_ACCENT,
    "activeforeground": AI_GLOW,
    "relief": "flat",
    "cursor": "hand2",
    "padx": dims['padding'],
    "pady": dims['padding']//2
}

search_button = tk.Button(search_content, 
                         text="⚡ Search", 
                         command=lambda: asyncio.run(search()),
                         **button_style)
search_button.pack(side=tk.LEFT, padx=5)

temp_button = tk.Button(search_content, 
                       text="🌡 Temperature", 
                       command=lambda: asyncio.run(show_temperature(
                           map_widget.get_position()[0],
                           map_widget.get_position()[1]
                       )),
                       **button_style)
temp_button.pack(side=tk.LEFT, padx=5)

pressure_button = tk.Button(search_content, 
                          text="💨 Air Pressure", 
                          command=lambda: asyncio.run(show_pressure(
                              map_widget.get_position()[0],
                              map_widget.get_position()[1]
                          )),
                          **button_style)
pressure_button.pack(side=tk.LEFT, padx=5)

# Style the result label
result_label = tk.Label(results_frame,
                       font=("Helvetica", dims['normal_font_size']),
                       bg=AI_DARK,
                       fg=AI_TEXT,
                       justify=tk.LEFT,
                       wraplength=dims['window_width'] * 0.8)
result_label.pack(fill=tk.X, pady=dims['padding'])

# Graph Frame for temperature history
graph_frame = tk.Frame(results_frame, bg="#2C3E50")
graph_frame.pack(pady=5, fill=tk.BOTH, expand=True)

# Style the map mode frame
map_mode_frame = tk.Frame(controls_frame, bg=AI_DARK)
map_mode_frame.pack(pady=5, fill=tk.X)

# Create a frame for map mode buttons
map_buttons_container = tk.Frame(map_mode_frame, bg=AI_DARK)
map_buttons_container.pack(expand=True)

map_button_style = button_style.copy()
map_button_style["font"] = ("Helvetica", 11)
map_button_style["padx"] = 10

# Create list to store map mode buttons
map_mode_buttons = []

for text, mode in [
    ("📍 Street View", "https://tile.openstreetmap.org/{z}/{x}/{y}.png"),
    ("🛰 Satellite", "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"),
    ("🗺 Terrain", "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"),
    ("🌍 Hybrid", "https://mt1.google.com/vt/lyrs=y,h&x={x}&y={y}&z={z}")
]:
    button = tk.Button(map_buttons_container, text=text, command=lambda m=mode: set_map_mode(m),
              **map_button_style)
    button.pack(side=tk.LEFT, padx=5)
    map_mode_buttons.append(button)

# Map Widget - Create with higher accuracy settings
map_widget = tkintermapview.TkinterMapView(
    map_container,
    width=int(dims['window_width'] * 0.9),
    height=int(dims['window_height'] * 0.5),
    corner_radius=dims['padding']
)
map_widget.pack(fill=tk.BOTH, expand=True)

# Set higher precision coordinates (more decimal places)
map_widget.set_position(19.076090, 72.877426)  # More precise coordinates
map_widget.set_zoom(13)  # Changed from 14 to 13 for consistency
map_widget.set_tile_server("https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}")

# Add these new functions after the get_weather function
async def show_temperature(lat, lon):
    async with aiohttp.ClientSession() as session:
        data = await fetch_weather(session, lat, lon)
    
    if "error" in data:
        messagebox.showerror("Error", f"Failed to get data: {data['error']}")
        return
    
    try:
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        temp_min = data["main"]["temp_min"]
        temp_max = data["main"]["temp_max"]
        
        result_label.config(text=f"🌡 Temperature Details:\n"
                               f"Current: {temp}°C\n"
                               f"Feels like: {feels_like}°C\n"
                               f"Min: {temp_min}°C\n"
                               f"Max: {temp_max}°C", fg="white")
    except (KeyError, TypeError):
        messagebox.showerror("Error", "Could not parse weather data. Please try again.")

async def show_pressure(lat, lon):
    async with aiohttp.ClientSession() as session:
        data = await fetch_weather(session, lat, lon)
    
    if "error" in data:
        messagebox.showerror("Error", f"Failed to get data: {data['error']}")
        return
    
    try:
        pressure = data["main"]["pressure"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        
        result_label.config(text=f"💨 Air Pressure Details:\n"
                               f"Pressure: {pressure} hPa\n"
                               f"Humidity: {humidity}%\n"
                               f"Wind Speed: {wind_speed} m/s", fg="white")
        
    except KeyError:
        messagebox.showerror("Error", "Invalid response from API")

# Add this new function to fetch historical data
async def fetch_historical_temp(session, lat, lon):
    # Get last 24 hours data using One Call API 3.0
    url = f"https://api.openweathermap.org/data/3.0/onecall/timemachine?lat={lat}&lon={lon}&dt={int(datetime.now().timestamp())}&appid={API_KEY}&units=metric"
    try:
        async with session.get(url) as response:
            return await response.json()
    except Exception as e:
        return {"error": str(e)}

# Add a pulsing effect to the header (optional)
def pulse_header():
    current_fg = header_label.cget("fg")
    new_fg = AI_TEXT if current_fg == AI_GLOW else AI_GLOW
    header_label.configure(fg=new_fg)
    root.after(1500, pulse_header)  # Pulse every 1.5 seconds

pulse_header()

# Run main loop
root.mainloop()


