from datetime import datetime
import requests
from bs4 import BeautifulSoup
import os
from tqdm import tqdm
import fitz
import io
from PIL import Image
import cv2
import os
import numpy
from datetime import datetime
import pandas as pd


def get_details():
    connection_string = 'DefaultEndpointsProtocol=https;AccountName=trademarksearch;AccountKey=wKAxr8uwcNoWFmEqC7Cb19fCuWMKj3UUfitXG6uh+hI0KZbRSNlysyUswi2a2SzmjH4WkGgarH+U+ASt8ml5/g==;EndpointSuffix=core.windows.net'
    container_name = 'trademark-data'
    return connection_string, container_name


def get_clients_with_connection_string():
    connection_string, container_name = get_details()
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    return container_client


def upload_blob_with_connection_string(bytes, blob_name):
    connection_string, container_name = get_details()
    blob = BlobClient.from_connection_string(connection_string, container_name=container_name, blob_name=blob_name)
    exists = blob.exists()
    if not exists:
        blob.upload_blob(bytes)


def fetch_journal(link):
    headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Origin': 'https://search.ipindia.gov.in',
    'Referer': 'https://search.ipindia.gov.in/IPOJournal/Journal/Trademark',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    }

    data = {
        'FileName': link,
    }

    response = requests.post('https://search.ipindia.gov.in/IPOJournal/Journal/ViewJournal', headers=headers, data=data)
    return response.content


def extract_metadata(text):
    date_index_found = False
    class_index_found = False
    journal_no = 0
    class_no = 0
    app_no = 0
    date = 0
    text_split = text.split('\n')
    for index, item in enumerate(text_split):
        if date_index_found and class_index_found:
            break
        if 'Class' in item:
            if "Multi" in item or "multi" in item:
                class_no = 999
            else:
                try:
                    class_no = int(item.strip().split('Class')[-1].strip())
                except:
                    try:
                        class_no = int(text.split('\n')[index + 1].strip())
                    except:
                        class_no = 0
            journal_no = item.strip().split('No:')[-1].split(',')[0].strip()
            class_index_found = True
            class_index = index
        for split_chunk in item.split(' '):
            if 'Class' not in item and 'class' not in item:
                try:
                    date = datetime.strptime(split_chunk, '%d/%m/%Y')
                    app_no = int(item.strip().split(' ')[0])
                    date_index_found = True
                    date_index = index
                    break
                except:
                    continue
    if date_index_found and class_index_found:
        other_data = [x for i, x in enumerate(text.split('\n')) if i != date_index and i != class_index]
        other_data = [x.strip() for x in other_data if x.strip() != '']
        other_data = '\n'.join(other_data)
    else:
        other_data = None
    try:
        page_number = int(text_split[-2])
    except:
        page_number = 0
    return {'journal': journal_no, 'class': class_no, 'application': app_no, 'date': date, 'details': other_data, 'page': page_number}


def get_application_numbers(journal_file, basename):
    application_number_list = []
    page_number_dict = {}
    if "CLASS" not in basename:
        print("Ignoring file!")
        return []
    pdf_file = fitz.open(stream=journal_file, filetype="pdf")
    for page_index in range(len(pdf_file)):
        try:
            page = pdf_file[page_index]
        except:
            print(f"Check page {page_index} in file {basename}")
            continue
        text = page.get_text()
        metadata = extract_metadata(text)
        application_number_list.append(metadata['application'])
        page_number_dict[metadata['application']] = metadata['page']
    return application_number_list, page_number_dict


def get_application_numbers_from_pdf(journal_file):
    application_number_list = []
    page_number_dict = {}
    basename = os.path.basename(journal_file)
    if "CLASS" not in basename:
        print("Ignoring file!")
        return []
    pdf_file = fitz.open(journal_file, filetype="pdf")
    for page_index in range(len(pdf_file)):
        try:
            page = pdf_file[page_index]
        except:
            print(f"Check page {page_index} in file {basename}")
            continue
        text = page.get_text()
        metadata = extract_metadata(text)
        application_number_list.append(metadata['application'])
        if metadata['application'] in page_number_dict:
            page_number_dict[metadata['application']].append(metadata['page'])
        else:
            page_number_dict[metadata['application']] = [metadata['page']]
    return application_number_list, page_number_dict


def journal_scraping():
    response = requests.get('https://search.ipindia.gov.in/IPOJournal/Journal/Trademark')
    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table', id="Journal")
    rows = table.find_all('tr')
    latest_journal = rows[1].find_all('td')
    date_format = '%d/%m/%Y'
    for index, item in enumerate(latest_journal):
        if index == 0:
            if item.text == '1':
                continue
            else:
                raise Exception("Check code, the journal being scraped is not latest!")
        if index == 1:
            journal_no = item.text
            journal_dir = journal_no
            isExist = os.path.exists(journal_dir)
            if not isExist:
                os.makedirs(journal_dir)
        if index == 2:
            pub_date = datetime.strptime(item.text, date_format)
        if index == 3:
            avb_date = datetime.strptime(item.text, date_format)
        if index == 4:
            form_elements = item.find_all('form')
            application_numbers = []
            page_num_dict = {}
            for element in tqdm(form_elements):
                link = element.find('input')['value']
                basename = element.text.strip()
                filename = journal_dir + '/' + basename + '.pdf'
                if os.path.exists(filename):
                    continue
                journal_file = fetch_journal(link)
                with open(filename, 'wb') as f:
                    f.write(journal_file)
                application_numbers_file, page_num_dict_file = get_application_numbers(journal_file, basename)
                application_numbers += application_numbers_file
                page_num_dict.update(page_num_dict_file)
                # upload_blob_with_connection_string(journal_file, 'journals/' + filename)
    return set(application_numbers), page_num_dict
