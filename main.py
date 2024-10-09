import json
import requests
import sys
import os
from PIL import Image
from io import BytesIO
from pypdf import PdfWriter


def download_urls(urls) -> list[BytesIO]:
    total = len(urls)
    data = []
    for index, url in enumerate(urls, start=1):
        # display progress bar
        sys.stdout.write(f"\r\033[Kdownloading {url}\n")
        progress = int((index / total) * 100)
        sys.stdout.write("[" + "=" * progress + " " * (100 - progress) + f"] {index}/{total}")
        sys.stdout.flush()
        
        # download data
        response = requests.get(url)
        data.append(BytesIO(response.content))
    print()
    return data


# declare the json path
BOOKS_PATH = "books.json"

# read the json file into memory
with open(BOOKS_PATH, "r") as file:
    books_data = json.load(file)

# display all books
for index, book in enumerate(books_data, start=1):
    name = book["name"]
    print(f"{index}. {name}")
    
# get the user input
book_index = int(input("Enter the book number: "))
selected_book = books_data[book_index - 1]

# check if the pdf is already downloaded
name = selected_book["name"]
file = f"{name}.pdf"
if file in os.listdir():
    print(f"PDF already downloaded as '{file}'")
    sys.exit()

    
if "url" in selected_book and "pages" in selected_book:
    # download all pages of the book
    urls = [selected_book["url"].format(page) for page in range(1, selected_book["pages"] + 1)]
    images = [Image.open(data) for data in download_urls(urls)]
    
    # save as a pdf
    images[0].save(file, save_all=True, append_images=images[1:])
    print(f"PDF saved as '{file}'")
elif "urls" in selected_book:
    # download and merge pdfs
    writer = PdfWriter()
    for data in download_urls(selected_book["urls"]):
        writer.append(data)

    # save the merged pdf
    with open(file, "wb") as f:
        writer.write(f)

    print(f"PDFs merged and saved as '{file}'")
else:
    print("Invalid book format")