import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import geopandas as gpd
from dotenv import load_dotenv
from pyogrio import read_dataframe
from tqdm import tqdm

load_dotenv()
# Insert the API key
key = os.getenv("MAPS_API_KEY")
scrape_type = 0
samples_per_country = 400
pano = True
num_workers = 5
image_list = []
# Cache to store loaded GeoDataFrames to prevent reloading
gdf_cache = {}

# Load the JSON file as a dictionary
json_file_path = './regions_to_countries.json'
with open(json_file_path, 'r') as f:
    regions_to_countries_dict = json.load(f)

# Dictionary to map regions to shapefiles
region_shp_paths = {
    "Region 1": './GRIP4/GRIP4_Region1_vector_shp/GRIP4_region1.shp',
    "Region 2": './GRIP4/GRIP4_Region2_vector_shp/GRIP4_region2.shp',
    "Region 3": './GRIP4/GRIP4_Region3_vector_shp/GRIP4_region3.shp',
    "Region 4": './GRIP4/GRIP4_Region4_vector_shp/GRIP4_region4.shp',
    "Region 5": './GRIP4/GRIP4_Region5_vector_shp/GRIP4_region5.shp',
    "Region 6": './GRIP4/GRIP4_Region6_vector_shp/GRIP4_region6.shp',
    "Region 7": './GRIP4/GRIP4_Region7_vector_shp/GRIP4_region7.shp'
}


def load_shapefile_for_country(country):
    """
    Loads the shapefile for the given country based on the region it belongs to.

    Parameters:
        country (str): The name of the country to load the shapefile for.

    Returns:
        gpd.GeoDataFrame: The GeoDataFrame containing road geometries for the region of the country.

    Raises:
        ValueError: If the shapefile path for the region is not found or the country is not found in any region.
    """
    # Loop through each region in the JSON file to find which region the country belongs to
    for region, countries in regions_to_countries_dict.items():
        if country in countries:
            # If region is cached, use the cached GeoDataFrame
            if region in gdf_cache:
                print(f"Using cached GeoDataFrame for {region}")
                return gdf_cache[region]
            else:
                # Load the shapefile for the region and cache it for future use
                shapefile_path = region_shp_paths.get(region)
                if shapefile_path:
                    print(f"Loading shapefile for {region}: {shapefile_path}")
                    gdf = read_dataframe(shapefile_path)
                    gdf_cache[region] = gdf
                    return gdf
                else:
                    raise ValueError(f"Shapefile path for {region} not found.")
    # If the country is not found in the JSON data, raise an error
    raise ValueError(f"{country} not found in any region.")

# The following function is adapted from Street_View_API_scraping https://github.com/BLorenzoF/Street_View_API_scraping.git
def generate_ll(gdf, n2d=200):
    """
    Generates latitude and longitude coordinates for sampling from road geometries.

    Parameters:
        gdf (GeoDataFrame): GeoDataFrame containing the road geometries of the country.
        n2d (int): Number of points to generate (default is 200).

    Returns:
        list: A list of latitude, longitude, and heading (N, E, S, W) for each sample point.
    """
    # Calculate the number of roads to sample based on the desired number of points
    n_roads = int(n2d / 2)
    ll_list = []

    # Sample the roads if the dataset contains more roads than needed
    roads = gdf.sample(n=n_roads) if len(gdf) > n_roads else gdf

    # Loop through each road and extract latitude and longitude for sampling
    for road in roads['geometry']:
        if road.geom_type == 'LineString':
            lat, lon = road.xy[1][0], road.xy[0][0]
        elif road.geom_type == 'MultiLineString':
            # In case of multiple lines, take the first line segment
            first_line = road.geoms[0]
            lat, lon = first_line.xy[1][0], first_line.xy[0][0]
        else:
            continue

        # Create sample points at cardinal directions: North, East, South, West
        point_N = (lat, lon, 2)
        point_E = (lat, lon, 92)
        point_S = (lat, lon, 182)
        point_W = (lat, lon, 272)

        # Append the generated points to the list
        ll_list.append(point_N)
        ll_list.append(point_E)
        ll_list.append(point_S)
        ll_list.append(point_W)

    return ll_list

# The following function is adapted from Street_View_API_scraping https://github.com/BLorenzoF/Street_View_API_scraping.git
def MetaParse(MetaUrl):
    """
    Fetches and parses the metadata from the Google Street View API.

    Parameters:
        MetaUrl (str): The URL to request metadata from the Google Street View API.

    Returns:
        tuple: A tuple containing the date, panorama ID, latitude, and longitude if successful, otherwise None.
    """
    try:
        # Send a request to the provided metadata URL
        response = urllib.request.urlopen(MetaUrl)
        jsonRaw = response.read()
        jsonData = json.loads(jsonRaw)

        # Check if the response contains valid data and extract metadata
        if jsonData['status'] == "OK":
            return (jsonData.get('date', None), jsonData['pano_id'], jsonData['location']['lat'], jsonData['location']['lng'])
        else:
            return None
    except Exception as e:
        # Catch and print any errors that occur during the metadata fetch
        print(f"Error fetching metadata: {e}")
        return None


# The following function is adapted from Street_View_API_scraping https://github.com/BLorenzoF/Street_View_API_scraping.git
def GetStreetLL(Lat, Lon, Head, SaveLoc, retries=3):
    """
    Downloads a Street View image from the given latitude, longitude, and heading.

    Parameters:
        Lat (float): The latitude of the location.
        Lon (float): The longitude of the location.
        Head (int): The heading in degrees (N, E, S, W).
        SaveLoc (str): The directory where the image will be saved.
        retries (int): Number of retry attempts for downloading the image (default is 3).

    Returns:
        tuple: A tuple containing metadata and the success flag (1 for success, 0 for failure).
    """
    # Construct the base URL for fetching the Street View image
    base = r"https://maps.googleapis.com/maps/api/streetview"
    size = r"?size=640x640&fov=120&location="
    end = f"{Lat},{Lon}&heading={Head}&key={key}"
    MyUrl = base + size + end
    MetaUrl = base + r"/metadata" + size + end

    for attempt in range(retries):
        try:
            # Fetch metadata for the location
            met_data = MetaParse(MetaUrl)
            if met_data:
                date, pano_id, lat, lon = met_data
                if pano_id:
                    # Construct the filename and save the image
                    filename = f"{lat}_{lon}_{int(Head)}.jpg"
                    urllib.request.urlretrieve(MyUrl, os.path.join(SaveLoc, filename))
                    return [(date, pano_id, lat, lon, filename), 1]
        except urllib.error.HTTPError as e:
            # Handle HTTP errors and retry after a delay
            print(f"HTTPError: {e}, retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            # Handle other exceptions and print the error message
            print(f"Error downloading image: {e}")
            return None, 0

    # If all retry attempts fail, return failure
    return None, 0


def download_images_from_country(country_name, total_images_to_download, save_dir):
    """
    Downloads images from Google Street View for a given country.

    Parameters:
        country_name (str): The name of the country to scrape images from.
        total_images_to_download (int): The total number of images to download for the country.
        save_dir (str): The directory where the images will be saved.

    Returns:
        None
    """
    # Load the shapefile containing the road geometries for the country
    gdf = load_shapefile_for_country(country_name)
    images_downloaded = 0

    # Continue downloading images until the required number of images is reached
    while images_downloaded < total_images_to_download * 4:
        n2d = total_images_to_download - int(images_downloaded / 4)
        data_list = generate_ll(gdf, n2d)

        if not data_list:
            print("No points generated, exiting.")
            break

        # Use a thread pool to download images concurrently
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(GetStreetLL, i[0], i[1], i[2], save_dir)
                for i in data_list
            ]

            # Process the results from the threads
            for future in tqdm(as_completed(futures), total=len(futures),
                               desc=f'Downloading Images from {country_name}'):
                try:
                    result = future.result()
                    if result:
                        image_metadata, images_downloaded_in_current_iteration = result
                        images_downloaded += images_downloaded_in_current_iteration

                        if image_metadata:
                            image_list.append(image_metadata)
                except Exception as e:
                    print(f"Error downloading image: {e}")

    print(f"Downloaded {images_downloaded} images from {country_name}.")

def start_menu():
    """
    Displays the main menu for the Street View scraper and handles user input for navigation.

    Returns:
        None
    """
    choice = 0
    while choice != 3:
        print(f"Welcome to the StreetView scraper {datetime.now()}\n")
        print(f"---" * 10 + "\n")
        print("*** StreetView Scraper ***")
        print("0) Help")
        print("1) Settings")
        print("2) Start Scrape")
        print("3) Exit")
        choice = int(input("> "))
        if choice == 1:
            settings()
        elif choice == 2:
            start()
        elif choice != 3:
            help(0)

def help(i):
    """
    Displays a help menu with information about the scraper's functionality.

    Parameters:
        i (int): Help level or context, determines which help message to display.
                 0 - General help
                 1 - Settings help
                 2 - Scrape type help
                 3 - Panorama vs. Single Image help

    Returns:
        None
    """
    if i == 0:
        print("This is a tool for scraping images from Google Street View.\n")
        print("Make sure you have properly installed all dependencies.\n")
        print("Before you run a scrape, you need to properly configure your settings.\n")
        print("*** Commands ***")
        print("--- 0) Help ")
        print("------- Displays this help menu.")
        print("--- 1) Settings ")
        print("------- Configure settings for your scrape (API key, scrape type, etc.).")
        print("--- 2) Start Scrape ")
        print("------- Start the scrape using the current settings.")
        print("--- 3) Exit ")
        print("------- Exits the application.")

    elif i == 1:
        print("Settings allow you to configure key parameters for the scraper.\n")
        print("1) Set API Key: Input your Google Maps API key, which is required to use the Street View API.")
        print("2) Configure Scrape: Choose your scrape preferences, such as scraping individual countries or multiple countries from a file, setting the number of samples per country, and configuring the number of threads for concurrent downloads.")
        print("3) Back: Return to the main menu without saving changes.")

    elif i == 2:
        print("Scraping configuration options allow you to define how the scraper will behave.\n")
        print("1) Scrape Individual Countries: Allows you to input the name of a country and scrape images for that country.")
        print("2) Mass Scrape from File: Uses a file containing a list of country names to automatically scrape images for multiple countries.")
        print("3) Next: Proceed with the selected scrape configuration.")

    elif i == 3:
        print("You can choose between capturing panorama images or single images at each location.\n")
        print("1) Panorama: Capture multiple images at each point from different angles (N, E, S, W).")
        print("2) Single Image: Capture only one image per point at the location, without rotating the view.")
        print("3) Next: Proceed with the selected image capture mode.")

    else:
        print("Invalid help context. Please use a valid option.")

def settings():
    """
    Displays the settings menu for configuring the scraper's API key and scraping behavior.

    Returns:
        None
    """
    choice = 0
    while choice != 3:
        print("*** Settings ***")
        print("0) Help ")
        print("1) Set API key")
        print("2) Configure Scrape")
        print("3) Back")
        choice = int(input("> "))
        if choice == 1:
            setApiKey()
            print("Maps API key set.")
        elif choice == 2:
            configureScrape()
        elif choice != 3:
            help(1)

def setApiKey():
    """
    Prompts the user to enter their Google Maps API key and sets it globally.

    Returns:
        None
    """
    global key
    api_key = input("Enter your API key: ")
    key = api_key
    print("Key Set!")


def configureScrape():
    """
    Prompts the user to configure settings for how the scraper will behave, including the scrape type and number of samples per country.

    Returns:
        None
    """
    print("*** Configure Scrape ***")
    global scrape_type
    global pano
    global samples_per_country
    global num_workers

    # Loop through different configuration options
    choice = 0
    while choice != 3:
        print("How would you like to scrape?")
        print("0) Help")
        print("1) Scrape Individual Countries")
        print("2) Mass Scrape from File")
        print("3) Next")
        choice = int(input("> "))
        if choice == 1:
            scrape_type = 0
            break
        elif choice == 2:
            scrape_type = 1
            break
        elif choice != 3:
            help(2)

    choice = 0
    while choice != 3:
        print("Would you like to capture a panorama at each point? Or would you only like a single image per point?")
        print("0) Help")
        print("1) Panorama")
        print("2) Single Image")
        print("3) Next")
        choice = int(input("> "))
        if choice == 1:
            pano = True
            break
        elif choice == 2:
            pano = False
            break
        elif choice != 3:
            help(3)

    # Set the number of locations to sample from each country
    while True:
        print("How many locations would you like to sample from each country?")
        choice = abs(int(input("> ")))
        if choice > 0:
            samples_per_country = choice
            break
        else:
            print("Please enter a valid number.")

    # Set the number of threads for concurrent downloads
    while True:
        print("How many threads would you like to use?")
        choice = abs(int(input("> ")))
        if 1 <= choice <= os.cpu_count():
            num_workers = choice
            break
        else:
            print(f"Please enter a valid number between 1 and {os.cpu_count()}.")


def verify_config():
    """
    Verifies that the configuration is valid, primarily checking if the API key is set.

    Returns:
        bool: True if the configuration is valid, otherwise False.
    """
    return key is not None


def start():
    """
    Starts the scraping process after verifying that the configuration is valid.

    Returns:
        None
    """
    if verify_config():
        print("*** Starting Scrape ***")
        main()

def main():
    """
    Main function that starts the scraping process for individual countries or from a file.

    Returns:
        None
    """
    global image_list
    image_list = []
    DownLoc = "./Downloads"

    if scrape_type == 1:
        # Scrape multiple countries from a file
        file_path = 'countries_to_scrape.txt'

        with open(file_path, 'r') as file:
            countries_to_scrape = [line.strip() for line in file.readlines()]

        for country_name in countries_to_scrape:
            print(f"Starting scrape for {country_name}")
            country_dir = os.path.join(DownLoc, country_name)
            if not os.path.exists(country_dir):
                os.mkdir(country_dir)
                print(f'Created dir: {country_dir}\n')

            try:
                download_images_from_country(country_name, total_images_to_download=samples_per_country, save_dir=country_dir)
            except Exception as e:
                print(f"Error scraping images: {e}")
                continue

            print(f"Scrape completed for {country_name}\n")
    else:
        # Scrape an individual country
        country_name = input("What country would you like to scrape: ")
        print(f"Starting scrape for {country_name}")
        country_dir = os.path.join(DownLoc, country_name)
        if not os.path.exists(country_dir):
            os.mkdir(country_dir)
            print(f'Created dir: {country_dir}\n')

        try:
            download_images_from_country(country_name, total_images_to_download=samples_per_country, save_dir=country_dir)
        except Exception as e:
            print(f"Error scraping images: {e}")
        print(f"Scrape completed for {country_name}\n")

start_menu()