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
from pymongo import UpdateOne


start_index = 6200000
end_index = 6218500
num_processes = 8
journal_number = 2124
base_path = '/Volumes/Seagate Backup Plus Drive/'
base_path = ""
csv_folder = 'csvs_15_12'
image_folder = 'images_15_12'
image_folder_journal = image_folder + '_journal'
query_image_folder = 'vs_images'
report_output_folder = '2124_reports'
processed_csv = 'processed_15_12.csv'
application_numbers = [item for item in range(start_index, end_index)]
tm_collection = init_mongo_connection()
journal_application_numbers = list(journal_scraping())
application_numbers += journal_application_numbers
vs_data = pd.read_csv('vs_input.csv')
vs_data = vs_data[vs_data['Application No'].notna()].reset_index().drop('index', axis=1)
vs_application_numbers = vs_data['Application No'].to_list()
vs_application_numbers = [int(item) for item in vs_application_numbers]
existing_vs_data = mongo_application_search(tm_collection, vs_application_numbers)
existing_vs_application_numbers = []
new_vs_application_numbers = []
for data in existing_vs_data:
    existing_vs_application_numbers.append(data['Application Number'])

for number in vs_application_numbers:
    if number not in existing_vs_application_numbers:
        application_numbers.append(number)
        new_vs_application_numbers.append(number)

application_numbers = list(set(application_numbers))

### CRAWL DATA FOR APPLICATION NUMBERS FROM START_INDEX TO END_INDEX AND VS_APPS THAT ARE NEW
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

print(f"Scraping data from application number {start_index} to {end_index}, {len(new_vs_application_numbers)} query data and journal!")
pool = Pool(num_processes)
results = pool.map(generate_data, remaining)
# results = pool.map(generate_data_with_documents, remaining)


### COPY NEW IMAGES TO RESPECTIVE FOLDERS
print("Copying new query images to the query folder!")
all_images = []
for item in new_vs_application_numbers:
    all_images += glob.glob(f'{image_folder}/{item}*')

for image_path in all_images:
    shutil.copy(image_path, query_image_folder)

print("Copying new journal images to the journal folder!")
all_images = []
for item in journal_application_numbers:
    all_images += glob.glob(f'{image_folder}/{item}*')

isExist = os.path.exists(image_folder_journal)
if not isExist:
    os.makedirs(image_folder_journal)

for image_path in all_images:
    shutil.copy(image_path, image_folder_journal)


### UPDATE MONGODB DATABASE WITH THE LATEST CRAWLED DATA
paths = os.listdir(csv_folder)
df_list = []
for file in paths:
    df_list.append(pd.read_csv(os.path.join(csv_folder, file)))

results = pd.concat([item for item in df_list]).reset_index().drop('index', axis=1)
final_df = process_data(results)
final_df.to_csv(processed_csv)
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

### GENERATE IMAGE EMBEDDINGS FOR NEW QUERY DATA
query_image_embedding_folder = query_image_folder + '_embeddings'
isExist = os.path.exists(query_image_embedding_folder)
if not isExist:
    os.makedirs(query_image_embedding_folder)

existing_query_embeddings = glob.glob(query_image_embedding_folder + '/*')
query_embedding_df_list = []
for path in existing_query_embeddings:
    query_embedding_df_list.append(pd.read_csv(path, index_col=0))

query_embedding_df = pd.concat(query_embedding_df_list).reset_index().drop('index', axis=1)
existing_query_embeddings_application_numbers = query_embedding_df['Application Number'].to_list()
image_paths = []
for app_number in new_vs_application_numbers:
    images_for_app = glob.glob(f'{image_folder}/{app_num}*')
    image_paths += images_for_app

image_paths_split = int(len(image_paths)/num_processes)
image_paths = [image_paths[index: index + image_paths_split] for index in range(0, len(image_paths), image_paths_split)]
pool = Pool(num_processes)
results = pool.map(generate_image_embedding, image_paths)
existing_query_embeddings = glob.glob(query_image_embedding_folder + '/*')
query_embedding_df_list = []
for path in existing_query_embeddings:
    query_embedding_df_list.append(pd.read_csv(path, index_col=0, converters={'Embedding': pd.eval}))

query_embedding_df = pd.concat(query_embedding_df_list).reset_index().drop('index', axis=1)
