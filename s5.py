import tkinter as tk
from tkinter import messagebox
import tkintermapview
import asyncio
import aiohttp
import json
import os
import re
import threading

# Load API key from environment variable
API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "bfce929e6f2f0856b2b6761bad1f0cae")
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

# Caching dictionary for previously searched locations
CACHE_FILE = "location_cache.json"

def load_cache():
    """Load cached locations from a JSON file."""
    try:
        with open(CACHE_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_cache():
    """Save cached locations to a JSON file."""
    with open(CACHE_FILE, "w") as file:
        json.dump(location_cache, file)

location_cache = load_cache()

# Function to fetch weather data asynchronously
async def fetch_weather(session, lat, lon):
    url = f"{BASE_URL}?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    try:
        async with session.get(url) as response:
            return await response.json()
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
        
        result_label.config(text=f"🌡 Temperature: {temp}°C\n"
                                 f"☁ Condition: {weather_desc}\n"
                                 f"💧 Humidity: {humidity}%\n"
                                 f"🌬 Wind Speed: {wind_speed} m/s", fg="white")
    except KeyError:
        messagebox.showerror("Error", "Invalid response from API")

# Function to validate city name
def validate_city(city):
    return bool(re.match(r"^[a-zA-Z\s\-']+$", city))

# Function to search for a city and update the map (WITHOUT adding a pin)
async def search():
    city = city_entry.get().strip()
    if not city or not validate_city(city):
        messagebox.showerror("Error", "Please enter a valid city name")
        return
    
    # Check if the location is cached
    if city in location_cache:
        lat, lon = location_cache[city]
    else:
        url = f"https://nominatim.openstreetmap.org/search?q={city}&format=jsonv2&addressdetails=1&limit=1"
        headers = {"User-Agent": "WeatherMapApp/1.0 (contact@email.com)"}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    data = await response.json()
                    if data:
                        lat = float(data[0]['lat'])
                        lon = float(data[0]['lon'])
                        location_cache[city] = (lat, lon)  # Cache the location
                        save_cache()  # Save cache to file
                    else:
                        messagebox.showerror("Error", "Location not found")
                        return
            except Exception as e:
                messagebox.showerror("Error", f"Exception: {e}")
                return

    # Update map with new position WITHOUT adding any marker
    map_widget.set_position(lat, lon)
    map_widget.set_zoom(10)  # Default zoom to 15 for better accuracy

    # Fetch weather data
    await get_weather(lat, lon)

# Function to get weather on map click (WITHOUT adding a pin)
def on_map_click(coords):
    lat, lon = coords
    threading.Thread(target=asyncio.run, args=(get_weather(lat, lon),)).start()

# Function to switch map modes
def set_map_mode(mode):
    map_widget.set_tile_server(mode)

# Function to handle Enter key press
def on_enter(event):
    threading.Thread(target=asyncio.run, args=(search(),)).start()

# Create main window
root = tk.Tk()
root.title("Weather & Map Viewer")
root.geometry("900x750")
root.configure(bg="#2C3E50")  # Dark Mode Background

# Header
header_label = tk.Label(root, text="Weather & Map Viewer", font=("Arial", 20, "bold"), bg="#2C3E50", fg="white")
header_label.pack(pady=5)

# Search Frame
search_frame = tk.Frame(root, bg="#2C3E50")
search_frame.pack(pady=5)

city_entry = tk.Entry(search_frame, font=("Arial", 14), width=40)
city_entry.pack(side=tk.LEFT, padx=5)
city_entry.bind("<Return>", on_enter)  # Bind Enter key to search

search_button = tk.Button(search_frame, text="Search", font=("Arial", 12, "bold"), 
                          command=lambda: threading.Thread(target=asyncio.run, args=(search(),)).start(), 
                          bg="#2980B9", fg="white", relief="flat")
search_button.pack(side=tk.LEFT)

# Weather result label
result_label = tk.Label(root, text="Search a location or click on the map to get weather data", 
                        font=("Arial", 12, "italic"), bg="#2C3E50", fg="white")
result_label.pack(pady=5)

# Map Mode Buttons
map_mode_frame = tk.Frame(root, bg="#2C3E50")
map_mode_frame.pack(pady=5)

modes = [
    ("Street Mode", "https://tile.openstreetmap.org/{z}/{x}/{y}.png", "#7F8C8D"),
    ("Satellite Mode", "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", "#7F8C8D"),
    ("Terrain Mode", "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}", "#E67E22"),
    ("3D Mode", "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", "#E74C3C"),
    ("Hybrid Mode", "https://mt1.google.com/vt/lyrs=y,h&x={x}&y={y}&z={z}", "#F39C12"),
]

for name, url, color in modes:
    tk.Button(map_mode_frame, text=name, command=lambda u=url: set_map_mode(u), 
              bg=color, fg="white", relief="flat").pack(side=tk.LEFT, padx=5)

# Map Widget (WITHOUT markers)
map_widget = tkintermapview.TkinterMapView(root, width=850, height=450, corner_radius=10)
map_widget.pack(pady=10, side=tk.BOTTOM)
map_widget.set_position(19.0760, 72.8777)
map_widget.set_zoom(15)
map_widget.set_tile_server("https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}")
map_widget.add_right_click_menu_command("Get Weather", lambda coords: on_map_click(coords))

# Save cache and close application properly
root.protocol("WM_DELETE_WINDOW", lambda: [save_cache(), root.destroy()])

# Run main loop
root.mainloop()
