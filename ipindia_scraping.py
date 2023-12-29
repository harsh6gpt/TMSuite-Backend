import requests
from bs4 import BeautifulSoup
import io
import pandas as pd
from multiprocessing import Pool
from azure.storage.blob import BlobServiceClient, BlobClient
from fastai.vision import *
from pathlib import Path
import cv2 as cv
import numpy as np
import shutil
import uuid
from mongodb_helper import *


def delete_image_blob_azure(blob_name):
    connection_string, container_name = get_details()
    print(f'Deleting blob {blob_name}')
    blob = BlobClient.from_connection_string(connection_string, container_name=container_name, blob_name=f"processed_images/{blob_name}")
    blob.delete_blob()
    

def download_image_from_azure_to_file(local_folder, application_number):
    connection_string, container_name = get_details()
    print(f'Downloading image for {application_number}')
    blob = BlobClient.from_connection_string(connection_string, container_name=container_name, blob_name=f"processed_images/{application_number}_0.jpeg")
    with open(file=os.path.join(f"{local_folder}", f'{application_number}_0.jpeg'), mode="wb") as sample_blob:
        download_stream = blob.download_blob()
        sample_blob.write(download_stream.readall())


def multiprocess_download_image_from_azure_to_file(input_dict):
    connection_string, container_name = get_details()
    application_number = input_dict['application_number']
    local_folder = input_dict['local_folder']
    print(f'Downloading image for {application_number}')
    blob = BlobClient.from_connection_string(connection_string, container_name=container_name, blob_name=f"processed_images/{application_number}_0.jpeg")
    try:
        with open(file=os.path.join(f"{local_folder}", f'{application_number}_0.jpeg'), mode="wb") as sample_blob:
            download_stream = blob.download_blob()
            sample_blob.write(download_stream.readall())
    except:
        return


def check_image_exists(app_num):
    connection_string, container_name = get_details()
    blob = BlobClient.from_connection_string(connection_string, container_name, blob_name=f"processed_images/{app_num}_0.jpeg")
    exists = blob.exists()
    return exists


def create_directory_with_replacement(dir_name):
    isExist = os.path.exists(dir_name)
    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(dir_name)
    else:
        shutil.rmtree(dir_name)
        os.makedirs(dir_name)


def to_onehot(filename):
    code_dimension = 36
    captcha_dimension = 5
    code = filename.name.split('-')[0]
    encoding_dict = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'a': 10, 'b': 11, 
                     'c': 12, 'd': 13, 'e': 14, 'f': 15, 'g': 16, 'h': 17, 'i': 18, 'j': 19, 'k': 20, 'l': 21, 'm': 22, 
                     'n': 23, 'o': 24, 'p': 25, 'q': 26, 'r': 27, 's': 28, 't': 29, 'u': 30, 'v': 31, 'w': 32, 'x': 33, 
                     'y': 34, 'z': 35}
    onehot = np.zeros((code_dimension, captcha_dimension))
    for column, letter in enumerate(code):
        onehot[encoding_dict[letter], column] = 1
    return onehot.reshape(-1)


def decode(onehot):
    code_dimension = 36
    captcha_dimension = 5
    onehot = onehot.reshape(code_dimension, captcha_dimension)
    idx = np.argmax(onehot, axis=0)
    decoding_dict = {0: '0', 1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9', 10: 'a', 
                     11: 'b', 12: 'c', 13: 'd', 14: 'e', 15: 'f', 16: 'g', 17: 'h', 18: 'i', 19: 'j', 20: 'k', 
                     21: 'l', 22: 'm', 23: 'n', 24: 'o', 25: 'p', 26: 'q', 27: 'r', 28: 's', 29: 't', 30: 'u', 
                     31: 'v', 32: 'w', 33: 'x', 34: 'y', 35: 'z'}
    return [decoding_dict[i.item()] for i in idx]


def captcha_model_init(data_path, model_path):
    folder_path = Path(data_path)
    data = (ImageList.from_folder(folder_path)
        .split_by_rand_pct(0.2,42)
        .label_from_func(to_onehot, label_cls = FloatList) #making it a regression instead of classification (because this gave better results)
        .transform(size=(77,247))
        .databunch(bs=64))
    learn = cnn_learner(data, models.resnet50, model_dir='models', pretrained=False, path=Path(''), ps=0.1)
    learn.load(model_path)
    return learn


def get_details():
    connection_string = 'DefaultEndpointsProtocol=https;AccountName=trademarksearch;AccountKey=wKAxr8uwcNoWFmEqC7Cb19fCuWMKj3UUfitXG6uh+hI0KZbRSNlysyUswi2a2SzmjH4WkGgarH+U+ASt8ml5/g==;EndpointSuffix=core.windows.net'
    container_name = 'trademark-data'
    return connection_string, container_name


def get_clients_with_connection_string():
    connection_string, container_name = get_details()
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    return container_client


def init_session():
    cookies = {
    }

    headers = {
        'authority': 'ipindiaservices.gov.in',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9,hi;q=0.8',
        'cache-control': 'max-age=0',
        'referer': 'https://ipindiaservices.gov.in/',
        'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'frame',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    }

    response = requests.get('https://ipindiaservices.gov.in/eregister/Application_View.aspx', cookies=cookies, headers=headers)

    asp_id = response.headers['Set-Cookie'].split(';')[0].split('=')[1]
    soup = BeautifulSoup(response.content, 'html.parser')
    view_state = soup.find("input", {"id": "__VIEWSTATE"})['value']
    view_state_generator = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})['value']
    event_validation = soup.find("input", {"id": "__EVENTVALIDATION"})['value']
    return asp_id, view_state, view_state_generator, event_validation


def national_app_select(asp_id, view_state, view_state_generator, event_validation):
    cookies = {
        'ASP.NET_SessionId': asp_id,
    }

    headers = {
        'authority': 'ipindiaservices.gov.in',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9,hi;q=0.8',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://ipindiaservices.gov.in',
        'referer': 'https://ipindiaservices.gov.in/',
        'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'frame',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    }

    data = {
        'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=3.5.11119.20050, Culture=neutral, PublicKeyToken=28f01b0e84b6d53e:en-US:8e147239-dd05-47b0-8fb3-f743a139f982:865923e8:91bd373d:8e72a662:411fea1c:acd642d2:596d588c:77c58d20:14b56adc:269a19ae',
        '__EVENTTARGET': 'rdb$0',
        '__EVENTARGUMENT': '',
        '__LASTFOCUS': '',
        '__VIEWSTATE': view_state,
        '__VIEWSTATEGENERATOR': view_state_generator,
        '__VIEWSTATEENCRYPTED': '',
        '__EVENTVALIDATION': event_validation,
        'rdb': 'N',
    }

    response = requests.post(
        'https://ipindiaservices.gov.in/eregister/Application_View.aspx',
        cookies=cookies,
        headers=headers,
        data=data,
    )
    soup = BeautifulSoup(response.content, 'html.parser')
    view_state = soup.find("input", {"id": "__VIEWSTATE"})['value']
    view_state_generator = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})['value']
    event_validation = soup.find("input", {"id": "__EVENTVALIDATION"})['value']
    return view_state, view_state_generator, event_validation


def generate_captcha(asp_id):
    cookies = {
        'ASP.NET_SessionId': asp_id,
    }

    headers = {
        'authority': 'ipindiaservices.gov.in',
        'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9,hi;q=0.8',
        'referer': 'https://ipindiaservices.gov.in/',
        'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'image',
        'sec-fetch-mode': 'no-cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    }

    response = requests.get('https://ipindiaservices.gov.in/eregister/captcha.ashx', cookies=cookies, headers=headers)
    return response.content


def solve_captcha(captcha, learn):
    image = np.fromstring(captcha, np.uint8)
    image = cv.imdecode(image, cv.IMREAD_GRAYSCALE)
    _, thresh1 = cv.threshold(image, 140, 255, cv.THRESH_BINARY)
    image = cv.medianBlur(thresh1, 3)
    image = cv.imencode('.jpg', image)[1].tostring()
    image = open_image(io.BytesIO(image))
    _, pred_idx, _ = learn.predict(image)
    captch_result = "".join(decode(pred_idx))
    return captch_result


def retrieve_app_link(asp_id, view_state, view_state_generator, event_validation, app_num, captcha_result):
    cookies = {
        '_ga': 'GA1.1.1776609026.1687199508',
        'ASP.NET_SessionId': asp_id,
        '_ga_J735X1RHGE': 'GS1.1.1690565632.34.0.1690565632.0.0.0',
    }

    headers = {
        'authority': 'ipindiaservices.gov.in',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9,hi;q=0.8',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://ipindiaservices.gov.in',
        'referer': 'https://ipindiaservices.gov.in/',
        'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'frame',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    }

    data = {
        'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=3.5.11119.20050, Culture=neutral, PublicKeyToken=28f01b0e84b6d53e:en-US:8e147239-dd05-47b0-8fb3-f743a139f982:865923e8:91bd373d:8e72a662:411fea1c:acd642d2:596d588c:77c58d20:14b56adc:269a19ae',
        '__EVENTTARGET': '',
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': view_state,
        '__VIEWSTATEGENERATOR': view_state_generator,
        '__VIEWSTATEENCRYPTED': '',
        '__EVENTVALIDATION': event_validation,
        'applNumber': str(app_num),
        'captcha1': captcha_result,
        'btnView': 'View ',
    }

    response = requests.post(
        'https://ipindiaservices.gov.in/eregister/Application_View.aspx',
        cookies=cookies,
        headers=headers,
        data=data,
    )
    soup = BeautifulSoup(response.content, 'html.parser')
    view_state = soup.find("input", {"id": "__VIEWSTATE"})['value']
    view_state_generator = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})['value']
    event_validation = soup.find("input", {"id": "__EVENTVALIDATION"})['value']
    return soup, view_state, view_state_generator, event_validation


def retrieve_app_details(asp_id, view_state, view_state_generator, event_validation):
    cookies = {
        'ASP.NET_SessionId': asp_id,
    }

    headers = {
        'authority': 'ipindiaservices.gov.in',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9,hi;q=0.8',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://ipindiaservices.gov.in',
        'referer': 'https://ipindiaservices.gov.in/',
        'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'frame',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    }

    data = {
        'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=3.5.11119.20050, Culture=neutral, PublicKeyToken=28f01b0e84b6d53e:en-US:8e147239-dd05-47b0-8fb3-f743a139f982:865923e8:91bd373d:8e72a662:411fea1c:acd642d2:596d588c:77c58d20:14b56adc:269a19ae',
        '__EVENTTARGET': 'SearchWMDatagrid$ctl03$lnkbtnappNumber1',
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': view_state,
        '__VIEWSTATEGENERATOR': view_state_generator,
        '__VIEWSTATEENCRYPTED': '',
        '__EVENTVALIDATION': event_validation,
    }

    response = requests.post(
        'https://ipindiaservices.gov.in/eregister/Application_View.aspx',
        cookies=cookies,
        headers=headers,
        data=data,
    )
    soup = BeautifulSoup(response.content, 'html.parser')
    view_state = soup.find("input", {"id": "__VIEWSTATE"})['value']
    view_state_generator = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})['value']
    event_validation = soup.find("input", {"id": "__EVENTVALIDATION"})['value']
    app_details = soup.find('span', {'id': 'lblappdetail'})
    return soup, view_state, view_state_generator, event_validation, app_details


def retrieve_document_links(asp_id, view_state, view_state_generator, event_validation, button):
    cookies = {
        'ASP.NET_SessionId': asp_id,
    }
    headers = {
        'authority': 'ipindiaservices.gov.in',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9,hi;q=0.8',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://ipindiaservices.gov.in',
        'referer': 'https://ipindiaservices.gov.in/',
        'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'frame',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    }

    data = {
        'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=3.5.11119.20050, Culture=neutral, PublicKeyToken=28f01b0e84b6d53e:en-US:8e147239-dd05-47b0-8fb3-f743a139f982:865923e8:91bd373d:8e72a662:411fea1c:acd642d2:596d588c:77c58d20:14b56adc:269a19ae',
        '__EVENTTARGET': '',
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': view_state,
        '__VIEWSTATEGENERATOR': view_state_generator,
        '__VIEWSTATEENCRYPTED': '',
        '__EVENTVALIDATION': event_validation,
    }
    if button == "Uploaded Documents":
        data['btndocument'] = button
    if button == "Correspondence & Notices":
        data['btnNotice'] = button

    response = requests.post(
        'https://ipindiaservices.gov.in/eregister/Application_View.aspx',
        cookies=cookies,
        headers=headers,
        data=data,
    )
    soup = BeautifulSoup(response.content, 'html.parser')
    view_state = soup.find("input", {"id": "__VIEWSTATE"})['value']
    view_state_generator = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})['value']
    event_validation = soup.find("input", {"id": "__EVENTVALIDATION"})['value']

    # app_details = soup.find('span', {'id': 'lblappdetail'})
    return soup, view_state, view_state_generator, event_validation


def retrieve_links_from_table_of_documents(soup, button):
    tables = soup.find('div', {'id': 'pnlPopup'}).find_all('table')
    if button == "Uploaded Documents":
        term_to_ignore = "Uploaded"
    if button == "Correspondence & Notices":
        term_to_ignore = "Correspondence"
    for table in tables:
        if term_to_ignore in str(table):
            continue
        else:
            relevant_table = table
    data = []
    if button == "Uploaded Documents":
        for row in relevant_table.find_all('tr')[1:]:  # Skip the header row
            columns = row.find_all('td')
            serial_no = columns[0].text.strip()
            doc_description = columns[1].text.strip()
            doc_date = columns[2].text.strip()
            view_link = columns[3].find('a')['href']
            data.append({
                'Serial No': serial_no,
                'Document Description': doc_description,
                'Document Date': doc_date,
                'View Link': view_link,
            })
    if button == "Correspondence & Notices":
        for row in table.find_all('tr')[1:]:  # Skip the header row
            columns = row.find_all('td')
            serial_no = columns[0].text.strip()
            corres_no = columns[1].text.strip()
            corres_date = columns[2].text.strip()
            subject = columns[3].text.strip()
            despatch_no = columns[4].text.strip()
            despatch_date = columns[5].text.strip()
            view_link = columns[6].find('a')['href']
            data.append({
                'Serial No': serial_no,
                'Correspondence No': corres_no,
                'Correspondence Date': corres_date,
                'Subject': subject,
                'Despatch No': despatch_no,
                'Despatch Date': despatch_date,
                'View Link': view_link,
                'Document Description': subject,
            })
    return data


def retrieve_trademark_document(asp_id, link):
    cookies = {
    'ASP.NET_SessionId': asp_id,
    }
    headers = {
        'authority': 'ipindiaservices.gov.in',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9,hi;q=0.8',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    }
    response = requests.get(
        f'https://ipindiaservices.gov.in/eregister/{link}',
        cookies=cookies,
        headers=headers,
    )
    return response


def exit_app_details(asp_id, view_state, view_state_generator, event_validation):
    cookies = {
        'ASP.NET_SessionId': asp_id,
    }

    headers = {
        'authority': 'ipindiaservices.gov.in',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9,hi;q=0.8',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://ipindiaservices.gov.in',
        'referer': 'https://ipindiaservices.gov.in/',
        'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'frame',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    }

    data = {
        'ToolkitScriptManager1_HiddenField': ';;AjaxControlToolkit, Version=3.5.11119.20050, Culture=neutral, PublicKeyToken=28f01b0e84b6d53e:en-US:8e147239-dd05-47b0-8fb3-f743a139f982:865923e8:91bd373d:8e72a662:411fea1c:acd642d2:596d588c:77c58d20:14b56adc:269a19ae',
        '__EVENTTARGET': '',
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': view_state,
        '__VIEWSTATEGENERATOR': view_state_generator,
        '__VIEWSTATEENCRYPTED': '',
        '__EVENTVALIDATION': event_validation,
        'btnExit': 'EXIT',
    }

    response = requests.post(
        'https://ipindiaservices.gov.in/eregister/Application_View.aspx',
        cookies=cookies,
        headers=headers,
        data=data,
    )
    soup = BeautifulSoup(response.content, 'html.parser')
    view_state = soup.find("input", {"id": "__VIEWSTATE"})['value']
    view_state_generator = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})['value']
    event_validation = soup.find("input", {"id": "__EVENTVALIDATION"})['value']
    return soup, view_state, view_state_generator, event_validation


def extract_image(asp_id, image_url):
    cookies = {
        'ASP.NET_SessionId': asp_id,
    }

    headers = {
        'authority': 'ipindiaservices.gov.in',
        'accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9,hi;q=0.8',
        'referer': 'https://ipindiaservices.gov.in/',
        'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'image',
        'sec-fetch-mode': 'no-cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    }
    url = 'https://ipindiaservices.gov.in/eregister/' + image_url
    response = requests.get(
        url,
        cookies=cookies,
        headers=headers,
    )
    return response


def upload_df_to_blob_with_connection_string(df_byte, blob_name):
    connection_string, container_name = get_details()
    blob = BlobClient.from_connection_string(connection_string, container_name=container_name, blob_name=blob_name)
    blob.upload_blob(df_byte)


def get_other_document_links(soup):
    all_links = soup.find_all('a')
    output = []
    for item in all_links:
        if 'View' in item.text:
            output.append({'Document Description': item.text.split('View')[-1].strip(), 'View Link': item['href']})
    return output


def generate_data(app_nums_and_locations):
    app_nums = app_nums_and_locations[0]
    csv_path = app_nums_and_locations[1][0]
    image_path = app_nums_and_locations[1][1]
    learn = captcha_model_init(data_path='ipindia_captcha_processed', model_path='model')
    asp_id, view_state, view_state_generator, event_validation = init_session()
    view_state, view_state_generator, event_validation = national_app_select(asp_id, view_state, view_state_generator, event_validation)
    captcha = generate_captcha(asp_id)
    captcha_result = solve_captcha(captcha=captcha, learn=learn)
    data = []
    for app in app_nums:
        print(f"Processing application number - {app}")
        app_details = None
        num_tries = 0
        while app_details is None:
            try:
                soup, view_state, view_state_generator, event_validation = retrieve_app_link(asp_id, view_state, view_state_generator, event_validation, app, captcha_result)
                if 'No Matching Trade Marks' in soup.text:
                    app_details = 0
                    break
                soup, view_state, view_state_generator, event_validation, app_details = retrieve_app_details(asp_id, view_state, view_state_generator, event_validation)
                image_urls = soup.find_all('img')
                for index, image_url in enumerate(image_urls):
                    image = extract_image(asp_id, image_url['src'])
                    key = f"{app}_{index}"
                    with open(f'{image_path}/{key}.jpeg', 'wb') as file:
                        file.write(image.content)
                soup, view_state, view_state_generator, event_validation = exit_app_details(asp_id, view_state, view_state_generator, event_validation)
            except Exception as e:
                print(f"Exception {e} raised for {app}")
                num_tries += 1
                asp_id, view_state, view_state_generator, event_validation = init_session()
                view_state, view_state_generator, event_validation = national_app_select(asp_id, view_state, view_state_generator, event_validation)
                captcha = generate_captcha(asp_id)
                captcha_result = solve_captcha(captcha=captcha, learn=learn)
                if num_tries >= 5:
                    print(f"Number of tries exceeded 5 for {app}, bad data!")
                    break
                continue
        data.append(app_details)
    df = pd.DataFrame(list(zip(app_nums, [str(item) for item in data])), columns=['Application Number', 'Data'])
    filename = f'{csv_path}/' + str(uuid.uuid4()) + '.csv'
    df.to_csv(filename, index=False, encoding="utf-8")
    print(f"Saved file {filename}")
    return


def entry_ipindia(points_list, num_processes=8):
    pool = Pool(num_processes)
    # create_directory_with_replacement('images')
    # create_directory_with_replacement('csvs')
    results = pool.map(generate_data, points_list)
    return results


def generate_data_with_documents(app_nums_and_locations):
    documents_metadata_collection = init_mongo_connection('documents-metadata')
    app_nums = app_nums_and_locations[0]
    csv_path = app_nums_and_locations[1][0]
    image_path = app_nums_and_locations[1][1]
    base_path = app_nums_and_locations[1][2]
    image_path = base_path + image_path
    learn = captcha_model_init(data_path='ipindia_captcha_processed', model_path='model')
    asp_id, view_state, view_state_generator, event_validation = init_session()
    view_state, view_state_generator, event_validation = national_app_select(asp_id, view_state, view_state_generator, event_validation)
    captcha = generate_captcha(asp_id)
    captcha_result = solve_captcha(captcha=captcha, learn=learn)
    data = []
    metadata = []
    for app in app_nums:
        print(f"Processing application number - {app}")
        app_details = None
        num_tries = 0
        while app_details is None:
            try:
                soup, view_state, view_state_generator, event_validation = retrieve_app_link(asp_id, view_state, view_state_generator, event_validation, app, captcha_result)
                if 'No Matching Trade Marks' in soup.text:
                    app_details = 0
                    break
                soup, view_state, view_state_generator, event_validation, app_details = retrieve_app_details(asp_id, view_state, view_state_generator, event_validation)
                image_urls = soup.find_all('img')
                for index, image_url in enumerate(image_urls):
                    image = extract_image(asp_id, image_url['src'])
                    key = f"{app}_{index}"
                    with open(f'{image_path}/{key}.jpeg', 'wb') as file:
                        file.write(image.content)
                other_links_for_documents = get_other_document_links(soup)
                button = "Uploaded Documents"
                soup, view_state, view_state_generator, event_validation = retrieve_document_links(asp_id, view_state, view_state_generator, event_validation, button)
                uploaded_documents_data = retrieve_links_from_table_of_documents(soup, button)
                button = "Correspondence & Notices"
                soup, view_state, view_state_generator, event_validation = retrieve_document_links(asp_id, view_state, view_state_generator, event_validation, button)
                notices_documents_data = retrieve_links_from_table_of_documents(soup, button)
                all_document_links = other_links_for_documents + uploaded_documents_data + notices_documents_data
                downloaded_docs = []
                for item in all_document_links:
                    try:
                        downloaded_docs.append({item['Document Description']: retrieve_trademark_document(asp_id, item['View Link'])})
                        print(f"For {app}, downloaded {item['Document Description']}")
                    except:
                        continue
                document_folder = f'{base_path}/documents_{csv_path}/{app}'
                isExist = os.path.exists(document_folder)
                if not isExist:
                    os.makedirs(document_folder)
                for doc in downloaded_docs:
                    key = list(doc.keys())[0]
                    filetype = doc[key].headers['Content-Type'].split(';')[0].split('/')[-1]
                    filename = f"{key}.{filetype}"
                    with open(f"{document_folder}/{filename}", 'wb') as f:
                        f.write(doc[key].content)
                soup, view_state, view_state_generator, event_validation = exit_app_details(asp_id, view_state, view_state_generator, event_validation)
            except Exception as e:
                print(f"Exception {e} raised for {app}")
                num_tries += 1
                asp_id, view_state, view_state_generator, event_validation = init_session()
                view_state, view_state_generator, event_validation = national_app_select(asp_id, view_state, view_state_generator, event_validation)
                captcha = generate_captcha(asp_id)
                captcha_result = solve_captcha(captcha=captcha, learn=learn)
                if num_tries >= 5:
                    print(f"Number of tries exceeded 5 for {app}, bad data!")
                    break
                continue
        data.append(app_details)
        for item in all_document_links:
            item['Application Number'] = app
        metadata += all_document_links
    df = pd.DataFrame(list(zip(app_nums, [str(item) for item in data])), columns=['Application Number', 'Data'])
    filename = f'{base_path}{csv_path}/' + str(uuid.uuid4()) + '.csv'
    df.to_csv(filename, index=False, encoding="utf-8")
    documents_metadata_collection.insert_many(metadata)
    print(f"Saved file {filename}")
    return


# def get_data_for_one_application(app_num):
# learn = captcha_model_init(data_path='ipindia_captcha_processed', model_path='model')
# asp_id, view_state, view_state_generator, event_validation = init_session()
# view_state, view_state_generator, event_validation = national_app_select(asp_id, view_state, view_state_generator, event_validation)
# captcha = generate_captcha(asp_id)
# captcha_result = solve_captcha(captcha=captcha, learn=learn)
# soup, view_state, view_state_generator, event_validation = retrieve_app_link(asp_id, view_state, view_state_generator, event_validation, app_num, captcha_result)
# soup, view_state, view_state_generator, event_validation, app_details = retrieve_app_details(asp_id, view_state, view_state_generator, event_validation)
# button = "Uploaded Documents"
# soup, view_state, view_state_generator, event_validation = retrieve_document_links(asp_id, view_state, view_state_generator, event_validation, button)
# uploaded_documents_data = retrieve_links_from_table_of_documents(soup, button)
# button = "Correspondence & Notices"
# soup, view_state, view_state_generator, event_validation = retrieve_document_links(asp_id, view_state, view_state_generator, event_validation, button)
# notices_documents_data = retrieve_links_from_table_of_documents(soup, button)
#     return soup