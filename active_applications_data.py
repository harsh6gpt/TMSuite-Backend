from ipindia_scraping import *
from journal_scraping import *
from process_data import *
from mongodb_helper import *
from visual_search import *
from phonetic_text_search import *
from generate_pdf_reports import *
import glob
import numpy as np
from sklearn.decomposition import PCA
from azure_helper import *


### GENERATE QUERY DATAFRAME USING ALL APPLICATION NUMBERS
all_blobs = list_application_number_blobs()
all_active_blobs = []
for item in tqdm(all_blobs):
    if 'active' in item and 'RKDewan' in item:
        all_active_blobs.append(item)


application_num_to_organization_dict = {}

for item in tqdm(all_active_blobs):
    excel_stream = download_app_num_blob_to_stream(item)
    organization = item.split('/')[-1].split('.')[0]
    application_numbers = pd.read_excel(excel_stream, index_col=0)['Application Number'].to_list()
    for number in application_numbers:
        if 'IRDI' in str(number):
            try:
                app_num = int(number.split('-')[1])
                if app_num in application_num_to_organization_dict:
                    application_num_to_organization_dict[app_num].append(organization)
                else:
                    application_num_to_organization_dict[app_num] = [organization]
            except:
                continue
        
        try:
            app_num = int(number)
            if app_num in application_num_to_organization_dict:
                application_num_to_organization_dict[app_num].append(organization)
            else:
                application_num_to_organization_dict[app_num] = [organization]
        except:
            continue


all_query_application_numbers = list(application_num_to_organization_dict.keys())
for key in application_num_to_organization_dict.keys():
    application_num_to_organization_dict[key] = list(set(application_num_to_organization_dict[key]))


### GET EXISTING ACTIVE APPLICATION DATA
tm_collection = init_mongo_connection()
existing_application_data = mongo_application_search(tm_collection, all_query_application_numbers)
existing_application_data_list = []
for data in existing_application_data:
    existing_application_data_list.append(data)

### INGEST NEW DATA FOR ACTIVE APPLICATIONS
application_numbers = all_query_application_numbers
base_path = ""
csv_folder = "csvs_active"
image_folder = "images_active"
isExist = os.path.exists(base_path + csv_folder)
if not isExist:
    os.makedirs(base_path + csv_folder)

isExist = os.path.exists(f'{base_path}documents_{csv_folder}')
if not isExist:
    os.makedirs(f'{base_path}documents_{csv_folder}')

isExist = os.path.exists(base_path + image_folder)
if not isExist:
    os.makedirs(base_path + image_folder)

paths = os.listdir(base_path + csv_folder)
df_list = []
for file in paths:
    df_list.append(pd.read_csv(os.path.join(base_path + csv_folder, file)))

downloaded_applications = []
for item in df_list:
    downloaded_applications += item['Application Number'].to_list()

remaining = []
for item in application_numbers:
    if item not in downloaded_applications:
        remaining.append(item)
    

gap = 100
remaining = [remaining[index:index+gap] for index in range(0, len(remaining), gap)]
remaining = [[item, (csv_folder, image_folder, base_path)] for item in remaining]

num_processes = 8
pool = Pool(num_processes)
results = pool.map(generate_data, remaining)

paths = os.listdir(csv_folder)
df_list = []
for file in paths:
    df_list.append(pd.read_csv(os.path.join(csv_folder, file)))

results = pd.concat([item for item in df_list]).reset_index().drop('index', axis=1)
final_df = process_data(results)
application_numbers = final_df['Application Number'].to_list()
db_output = mongo_application_search(tm_collection, application_numbers)
app_to_id_dict = {}
for output in db_output:
    app_num = output['Application Number']
    id_num = output['_id']
    app_to_id_dict[app_num] = id_num

records = final_df.to_dict(orient='records')
to_be_updated = []
new_data = []
for record in records:
    if record['Application Number'] in app_to_id_dict:
        to_be_updated.append(record)
    else:
        new_data.append(record)
    

tm_collection.insert_many(new_data)
update_operations_list = []
for record in to_be_updated:
    application_number = record['Application Number']
    update_operations_list.append(UpdateOne({'_id': app_to_id_dict[application_number]}, {'$set': record}, upsert=True))

# Update the existing document with the new data
result = tm_collection.bulk_write(update_operations_list)

### UPDATE MONGODB WITH ACTIVE APPS
insert_list = []
for index, item in enumerate(records):
    status_changed = 1
    for existing in existing_application_data_list:
        if item['Application Number'] == existing['Application Number']:
            if item['tm_status'] == existing['tm_status']:
                status_changed = 0
            else:
                status_changed = 1
    item['status_changed'] = status_changed
    for organization in application_num_to_organization_dict[item['Application Number']]:
        item['organization'] = organization
        insert_list.append(item)

active_collection = init_mongo_connection('active-application-data')
active_collection.insert_many(insert_list)