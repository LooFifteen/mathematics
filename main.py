import json
import requests
import sys
import os
import time
import magic
import img2pdf
from PIL import Image
from io import BytesIO
from pypdf import PdfWriter
from pypdf.constants import PageLabelStyle
from concurrent.futures import ThreadPoolExecutor


class PageLabel:
    def __init__(self, index_from: int, index_to: int, style: PageLabelStyle, prefix: str | None = None, start: int = 0):
        self.__index_from = index_from
        self.__index_to = index_to
        self.__style = style
        self.__prefix = prefix
        self.__start = start
        
    def apply(self, writer: PdfWriter):
        writer.set_page_label(self.__index_from - 1, self.__index_to - 1, self.__style, self.__prefix, self.__start)
        
    def from_json(data: dict) -> "PageLabel":
        return PageLabel(data["from"], data["to"], data["style"], data.get("prefix"), data.get("start", 0))
    
    
class URL:
    def __init__(self, url: str, pages: int = 1):
        self.__url = url
        self.__pages = pages
        
    def get_urls(self) -> list[str]:
        # if the book has only one page, return the url as a list
        if self.__pages == 1:
            return [self.__url]
        # return a list of urls with the page number formatted in
        return [self.__url.format(page) for page in range(1, self.__pages + 1)]
    
    def from_json(data: dict | str) -> "URL":
        # if the data is a string, return a URL with a single page
        if isinstance(data, str):
            return URL(data)
        return URL(data["url"], data.get("pages", 1))
    

class Book:
    def __init__(self, name: str, urls: list[URL], labels: list[PageLabel] = [], tags: list[str] = []):
        self.__name = name
        self.__urls = urls
        self.__labels = labels
        self.__tags = tags
        
    def download(self):
        # get all urls and flatten the list
        urls = [url.get_urls() for url in self.__urls]
        urls = [url for sublist in urls for url in sublist]
        
        # download all urls
        data = download_urls(urls)
        
        # find mime type of all downloaded data
        data = [(value, magic.Magic(mime=True).from_buffer(value.read())) for value in data]
        
        # group consecutive mime types
        groups: list[tuple[str, list[BytesIO]]] = []
        for value, mime in data:
            if not groups or groups[-1][0] != mime:
                groups.append([mime, []])
            groups[-1][1].append(value)
            
        # create the pdf
        pdfs: list[BytesIO] = []
        bar = ProgressBar(len(groups), "creating pdfs")
        for mime, values in groups:
            if mime.startswith("image"):
                pdfs.append(create_image_pdf(values))
            elif mime == "application/pdf":
                pdfs.extend(values)
            else:
                print(f"unsupported mime type: {mime}")
            bar.increment()
        print()
                
        # combine all pdfs into a single pdf
        writer = PdfWriter()
        bar = ProgressBar(len(pdfs), "combining pdfs")
        for pdf in pdfs:
            writer.append(pdf)
            bar.increment()
        print()

        # apply page labels if any
        bar = ProgressBar(len(self.__labels), "applying page labels")
        for label in self.__labels:
            label.apply(writer)
            bar.increment()
        print()

        # Save the final PDF
        file = f"{self.__name}.pdf"
        with open(file, "wb") as f:
            writer.write(f)
        print(f"saved as '{file}'")

        
    def get_name(self) -> str:
        return self.__name
    
    def get_tags(self) -> list[str]:
        return self.__tags
        
    def from_json(data: dict) -> "Book":
        return Book(
            data["name"],
            [URL.from_json(url) for url in data["urls"]],
            [PageLabel.from_json(label) for label in data.get("labels", [])],
            data.get("tags", [])
        )
        
        
def create_image_pdf(images: list[BytesIO]) -> BytesIO:
    return BytesIO(img2pdf.convert([image.getvalue() for image in images]))


class ProgressBar:
    def __init__(self, total: int, label: str):
        self.__total = total
        self.__current = 0
        self.__start_time = time.time()
        self.__label = label

    def increment(self):
        self.__current += 1
        self.display()

    def display(self):
        progress = int((self.__current / self.__total) * 100)
        sys.stdout.write(f"\r\033[K{self.__label} [{('=' * progress).ljust(100)}] {self.__current}/{self.__total} ({time.time() - self.__start_time:.2f}s)")
        sys.stdout.flush()


def download_url(url: str, progress_bar: ProgressBar) -> BytesIO:
    response = requests.get(url)
    progress_bar.increment()
    return BytesIO(response.content)

def download_urls(urls) -> list[BytesIO]:
    total = len(urls)
    progress_bar = ProgressBar(total, "downloading")
    data = []

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(download_url, url, progress_bar) for url in urls]
        for future in futures:
            data.append(future.result())
    print()

    return data


if __name__ == "__main__":
    # declare the json path
    BOOKS_PATH = "books.json"
    
    # read the json file into memory
    with open(BOOKS_PATH, "r") as file:
        books_data = json.load(file)
        
    # parse the json data into Book objects
    books: list[Book] = [Book.from_json(data) for data in books_data]
    
    # display all books
    for index, book in enumerate(books, start=1):
        print(f"{index}. {book.get_name()}")
        
    # get the user input
    book_index = int(input("Enter book number >> "))
    selected_book = books[book_index - 1]
    
    # download the book
    selected_book.download()