import folium
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import webbrowser

# Initialize the geocoder
geolocator = Nominatim(user_agent="route_mapper")

# Function to get coordinates from a place name
def get_coordinates(place_name):
    location = geolocator.geocode(place_name)
    if location:
        return (location.latitude, location.longitude)
    else:
        print(f"Could not find location for '{place_name}'. Please try again.")
        return None

# Get start and end locations from the user by name
start_place = input("Enter the name of the start location (city, village, or address): ")
end_place = input("Enter the name of the end location (city, village, or address): ")

# Convert place names to coordinates
start_location = get_coordinates(start_place)
end_location = get_coordinates(end_place)

# Check if both locations were found
if start_location and end_location:
    # Calculate the distance
    distance = geodesic(start_location, end_location).kilometers

    # Create a map centered at the midpoint of the two locations
    midpoint = ((start_location[0] + end_location[0]) / 2, (start_location[1] + end_location[1]) / 2)
    m = folium.Map(location=midpoint, zoom_start=6)

    # Add markers for the start and end points
    folium.Marker(start_location, tooltip=f"Start Location: {start_place}").add_to(m)
    folium.Marker(end_location, tooltip=f"End Location: {end_place}").add_to(m)

    # Draw the route as a polyline
    folium.PolyLine([start_location, end_location], color="blue", weight=2.5, opacity=1).add_to(m)

    # Add a popup to show the calculated distance at the midpoint
    folium.Marker(
        midpoint,
        tooltip=f"Distance: {distance:.2f} km",
        icon=folium.DivIcon(html=f'<div style="font-size: 12pt; color : blue">{distance:.2f} km</div>')
    ).add_to(m)

    # Save the map to an HTML file and open it in the default browser
    map_file = "route_map.html"
    m.save(map_file)
    webbrowser.open(map_file)

    print(f"The distance between '{start_place}' and '{end_place}' is approximately {distance:.2f} km.")
else:
    print("Unable to generate map due to missing location data.")
