import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from phonetics import metaphone, soundex
import numpy as np


def convert_to_int_app_num(x):
    try:
        return int(x)
    except:
        return 0
    

def class_tf(x):
    try:
        return int(x)
    except:
        if '99' in x:
            return 99
        else:
            return 0
        

def lower(x):
    try:
        return x.lower()
    except:
        if x == np.NaN:
            return str(0)


def metaphone_phonetics(x):
    try:
        return metaphone(x)
    except:
        return str(0)
    

def soundex_phonetics(x):
    try:
        return soundex(x)
    except:
        return str(0)
    

def clean_tm(x):
    try:
        return ''.join(letter for letter in x if letter.isalnum() or letter == " ")
    except:
        if x == np.NaN:
            return str(0)
        

def refine_data(data_list):
    date_format = '%d/%m/%Y'
    check_tm = []
    check_tm_app = []
    search_data_list = []
    useful_keys = ['Associated Trademarks', 'Class', 'Conditions', 'Country', 'Date of Application', 'Email Id',  'International Reg No.', 'Proprietor Address', 'Proprietor name', 
    'Publication Details', 'Restrictions', 'State', 'TM Application No.', 'TM Applied For', 'TM Category', 'Trade Mark Type', 'User Detail', 'Valid upto/ Renewed upto',
    'tm_status', 'Goods & Service Details', 'Agent name', 'Agent Address', 'Attorney name', 'Attorney Address']
    for index, item in enumerate(data_list):
        if 'Proprietor Name' in item:
            continue
        new_data = {}
        for key in useful_keys:
            try:
                new_data[key] = item[key]
            except:
                new_data[key] = None
        if 'User Detail' in item:
            try:
                used_date = datetime.strptime(item['User Detail'], date_format)
                new_data["Used Since"] = used_date
            except:
                new_data["Used Since"] = None
        try:
            new_data["TM Application No."] = int(new_data["TM Application No."])
        except:
            new_data["TM Application No."] = int(new_data["TM Application No."].split('-')[1])
        try:
            new_data["Valid upto/ Renewed upto"] = datetime.strptime(item["Valid upto/ Renewed upto"], date_format)
        except:
            new_data["Valid upto/ Renewed upto"] = None
            check_tm.append(index)
        try:
            new_data["Date of Application"] = datetime.strptime(item["Date of Application"], date_format)
        except:
            new_data["Date of Application"] = None
            check_tm_app.append(index)
        num_images = 0
        for i in range(1, 29):
            if f'Image Link {i}' in item:
                num_images = i
        new_data['Number of Images'] = num_images
        search_data_list.append(new_data)
    return pd.DataFrame.from_records(search_data_list)


def process_data(data):
    unique_keys = set()
    data_list = []
    for index, html in enumerate(data['Data']):
        app_num = data.loc[index]['Application Number']
        if html == '0':
            continue
        # Create a BeautifulSoup object
        soup = BeautifulSoup(str(html), 'html.parser')
        if soup.text == "":
            continue
        extracted_data = {}
        # Find all tables
        tables_list = soup.find_all('table', align="Center")
        for table_num, table in enumerate(tables_list):
            table_details = table.find_all('td')
            for table_detail in table_details:
                if "Status" in table_detail.text:
                    extracted_data['tm_status'] = table_detail.text.strip().split(":")[-1].strip()
                if "Alert" in table_detail.text:
                    extracted_data['tm_alert'] = table_detail.text.strip().split(":")[-1].strip()
        # Find the relevant table with the data
        data_table = soup.find('table', width='680px', cellspacing='0', style='font-size=larger; background-color:mintcream;')
        if data_table is None:
            continue
        # Initialize an empty dictionary to store the extracted information
        count_image = 0
        # Iterate through each row in the table and extract the data
        for row in data_table.find_all('tr'):
            columns = row.find_all('td')
            if len(columns) == 2:
                key = columns[0].text.strip()
                value = columns[1].text.strip()
                extracted_data[key] = value
            if len(columns) == 1:
                if 'Trade Mark Image' in columns[0].text.strip():
                    continue
                else:
                    count_image += 1
                    image_link = columns[0].find_all('img')[0]['src']
                    key = f"Image Link {count_image}"
                    value = image_link
                    extracted_data[key] = value
        unique_keys = unique_keys.union(set(extracted_data.keys()))
        data_list.append(extracted_data)
    final_df = refine_data(data_list)
    final_df['Wordmark'] = final_df['TM Applied For'].apply(lambda x: clean_tm(lower(x)))
    final_df['Metaphone'] = final_df['Wordmark'].apply(lambda x: metaphone_phonetics(clean_tm(x)))
    final_df['Soundex'] = final_df['Wordmark'].apply(lambda x: soundex_phonetics(clean_tm(x)))
    final_df['Application Number'] = final_df['TM Application No.'].apply(lambda x: convert_to_int_app_num(x))
    final_df['Class'] = final_df['Class'].apply(lambda x: class_tf(x))
    final_df['Used Since'] = final_df['Used Since'].astype(object).where(final_df['Used Since'].notnull(), None)
    final_df['Valid upto/ Renewed upto'] = final_df['Valid upto/ Renewed upto'].astype(object).where(final_df['Valid upto/ Renewed upto'].notnull(), None)
    final_df['Date of Application'] = final_df['Date of Application'].astype(object).where(final_df['Date of Application'].notnull(), None)
    final_df = final_df.rename(columns={'TM Application No.': 'TM Application No', 'International Reg No.': 'International Reg No'})
    return final_df
