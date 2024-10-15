import json
import requests
import sys
import os
import time
from PIL import Image
from io import BytesIO
from pypdf import PdfWriter
from pypdf.constants import PageLabelStyle
from concurrent.futures import ThreadPoolExecutor


class ProgressBar:
    def __init__(self, total: int):
        self.__total = total
        self.__current = 0
        self.__start_time = time.time()

    def increment(self):
        self.__current += 1
        self.display()

    def display(self):
        progress = int((self.__current / self.__total) * 100)
        sys.stdout.write(f"\r\033[K[{('=' * progress).ljust(100)}] {self.__current}/{self.__total} ({time.time() - self.__start_time:.2f}s)")
        sys.stdout.flush()


def download_url(url: str, progress_bar: ProgressBar) -> BytesIO:
    response = requests.get(url)
    progress_bar.increment()
    return BytesIO(response.content)

def download_urls(urls) -> list[BytesIO]:
    total = len(urls)
    progress_bar = ProgressBar(total)
    data = []

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(download_url, url, progress_bar) for url in urls]
        for future in futures:
            data.append(future.result())
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
    
    # rewrite page labels
    if "start" in selected_book:
        writer = PdfWriter(file)
        start_page = int(selected_book["start"])
        writer.set_page_label(0, start_page - 2, style=PageLabelStyle.LOWERCASE_ROMAN)
        writer.write(file)
        print("Page labels rewritten")
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