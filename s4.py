import tkinter as tk
from tkinter import messagebox
import tkintermapview
import requests
import asyncio
import aiohttp
import json

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

# Function to search for a city and update the map
async def search():
    city = city_entry.get().strip()
    if not city:
        messagebox.showerror("Error", "Please enter a city name")
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
                    else:
                        messagebox.showerror("Error", "Location not found")
                        return
            except Exception as e:
                messagebox.showerror("Error", f"Exception: {e}")
                return

    # Update map with new position
    map_widget.delete_all_marker()
    map_widget.set_position(lat, lon)
    map_widget.set_marker(lat, lon, text="📍")
    map_widget.set_zoom(15)  # Default zoom to 15 for better accuracy
    zoom_slider.set(15)  # Update slider to reflect zoom level

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
                          command=lambda: asyncio.run(search()), bg="#2980B9", fg="white", relief="flat")
search_button.pack(side=tk.LEFT)

# Weather result label (Now below search bar)
result_label = tk.Label(root, text="Search a location or click on the map to get weather data", font=("Arial", 12, "italic"), bg="#2C3E50", fg="white")
result_label.pack(pady=5)

# Map Mode Buttons (Placed above the map)
map_mode_frame = tk.Frame(root, bg="#2C3E50")
map_mode_frame.pack(pady=5)

tk.Button(map_mode_frame, text="Street Mode", command=lambda: set_map_mode("https://tile.openstreetmap.org/{z}/{x}/{y}.png"), 
          bg="#7F8C8D", fg="white", relief="flat").pack(side=tk.LEFT, padx=5)
tk.Button(map_mode_frame, text="Satellite Mode", command=lambda: set_map_mode("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"), 
          bg="#7F8C8D", fg="white", relief="flat").pack(side=tk.LEFT, padx=5)
tk.Button(map_mode_frame, text="Terrain Mode", command=lambda: set_map_mode("https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"), 
          bg="#E67E22", fg="white", relief="flat").pack(side=tk.LEFT, padx=5)
tk.Button(map_mode_frame, text="3D Mode", command=lambda: set_map_mode("https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"), 
          bg="#E74C3C", fg="white", relief="flat").pack(side=tk.LEFT, padx=5)
tk.Button(map_mode_frame, text="Hybrid Mode", command=lambda: set_map_mode("https://mt1.google.com/vt/lyrs=y,h&x={x}&y={y}&z={z}"), 
          bg="#F39C12", fg="white", relief="flat").pack(side=tk.LEFT, padx=5)

# Map Widget
map_widget = tkintermapview.TkinterMapView(root, width=850, height=450, corner_radius=10)
map_widget.pack(pady=10, side=tk.BOTTOM)
map_widget.set_position(19.0760, 72.8777)
map_widget.set_zoom(15)  # Default to 15 for better accuracy
map_widget.set_tile_server("https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}")  # Default to Terrain Mode
map_widget.add_right_click_menu_command("Get Weather", on_map_click)

# Zoom Slider Frame
zoom_frame = tk.Frame(root, bg="#2C3E50")
zoom_frame.place(relx=0.95, rely=0.95, anchor="se")

zoom_label = tk.Label(zoom_frame, text="🔍 Zoom", font=("Arial", 10), bg="#34495E", fg="white")
zoom_label.pack(side=tk.LEFT, padx=5)

zoom_slider = tk.Scale(zoom_frame, from_=5, to=20, orient=tk.HORIZONTAL,
                       command=lambda val: map_widget.set_zoom(int(val)), bg="#34495E", fg="white", length=150)
zoom_slider.set(15)
zoom_slider.pack(side=tk.RIGHT)

# Run main loop
root.mainloop()
