# Google Street View Scraper

This project is a Python-based scraper that uses the Google Maps Street View API to download images of streets from around the world. The scraper allows for flexible configuration, including selecting specific countries, mass scraping from a file, and choosing between panorama or single image captures.

## Table of Contents
1. [Project Overview](#project-overview)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Dataset Requirement](#dataset-requirement)
6. [Attribution](#attribution)
7. [License](#license)

## Project Overview
The **Google Street View Scraper** is designed to scrape images from Google Street View for specific countries. It leverages road shapefiles to identify valid locations for scraping and allows for multithreaded image downloading to speed up the process. This tool can be useful for projects involving geolocation, machine learning datasets, or visual exploration of specific areas.

### Features:
- Download Street View images for specific countries based on road shapefiles.
- Choose between downloading panoramic views or single images at each location.
- Multithreaded downloading for efficient data scraping.
- Flexible configuration to support both single country scrapes and mass scrapes from a list of countries.

## Installation

### Prerequisites
Before using the scraper, you need to install the following dependencies:
- Python 3.7+
- The libraries listed in `requirements.txt`.
- GRIP4 regional datasets

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/dcrew44/StreetViewScraper.git
   cd StreetViewScraper
   ```
2. Install the required Python packages:
    ```bash
   pip install -r requirements.txt
   ```
3. Set up your Google Maps API key in a `.env` file: Create a `.env` file in the root directory of the project and add the following line:
   ```bash
   MAPS_API_KEY=your_api_key_here
   ```
## Dataset Requirements
To properly run this scraper, you will need to download and use the **GRIP4 Regional Roads Dataset**. This dataset contains the road shapefiles necessary for scraping valid locations from specific countries.

### Download Instructions:
1. Visit the following page to download the GRIP Shapefiles for each region:
[Download GRIP Database](https://www.globio.info/download-grip-dataset)
2. After downloading, unzip the datasets then move the unzipped datasets for each region to the `GRIP4` directory within your project.

## Configuration
Before you start scraping, you need to configure the settings:

1. **API Key:** Make sure your Google Maps API key is set in the `.env` file.
2. **Scraping Preferences:** You can configure how the scraper behaves:
   - **Scrape Individual Countries:** You can scrape images for a specific country by entering the name when prompted.
   - **Mass Scrape from File:** Prepare a file `countries_to_scrape.txt` with a list of countries (one per line) and the scraper will download images for each country automatically.
   - **Panorama vs Single Image:** Choose whether to capture multiple images (panorama) or a single image at each location.
   - **Number of Samples:** Set how many locations you want to sample for each country.

## Usage
### Running the Scraper
To start the scraper, run the following command:
```bash
    python scraper.py
```
Once the program is running, you will be presented with a menu to configure your settings and start the scraping process. The scraper will save images in the `./Downloads` directory, organized by country.

## Example Workflow
1. **Start Menu:** Configure the API key and settings for your scrape.
2. **Scraping Options:** Choose between scraping an individual country or using a file to scrape multiple countries.
3. **Image Capture:** Select between capturing panoramas or single images.
4. **Start Scraping:** Begin the scraping process and monitor the progress via the console.

## Attribution

Some parts of the code were adapted from [Street_View_API_scraping](https://github.com/BLorenzoF/Street_View_API_scraping/tree/main). Credit is given to the original author for their contributions to the image downloading functionality.

Special thanks to the creators of the GRIP global roads database, which is essential for the functionality of this scraper. You can find more information about the dataset [here](https://www.globio.info/download-grip-dataset).

### GRIP4 Database Citation:
When using the GRIP database, citations and acknowledgements should be made as follows:

Meijer, J.R., Huijbregts, M.A.J., Schotten, C.G.J., and Schipper, A.M. (2018): Global patterns of current and future road infrastructure. *Environmental Research Letters*, 13-064006. Data is available at [www.globio.info](https://www.globio.info/download-grip-dataset).

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.
