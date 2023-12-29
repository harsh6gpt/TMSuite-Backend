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
all_journal_blobs = []
for item in tqdm(all_blobs):
    if 'journal' in item and 'RKDewan' in item:
        all_journal_blobs.append(item)


application_num_to_organization_dict = {}
for item in tqdm(all_journal_blobs):
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


### GET JOURNAL AND THE APPLICATION NUMBERS IN THE JOURNAL
journal_application_numbers, journal_page_dict = journal_scraping()
journal_application_numbers.remove(0)

### GET APPLICATION NUMBERS FROM JOURNAL FOLDER
journal_directory = '2136'
journal_files = glob.glob(journal_directory + '/*.pdf')
journal_application_numbers = []
journal_page_dict = {}
for journal in tqdm(journal_files):
    journal_file_application_numbers, journal_file_page_dict = get_application_numbers_from_pdf(journal)
    journal_application_numbers += list(set(journal_file_application_numbers))
    journal_page_dict.update(journal_file_page_dict)

journal_application_numbers = list(set(journal_application_numbers))
journal_application_numbers.remove(0)
del(journal_page_dict[0])
### MOVE IMAGES FOR JOURNAL FROM AZURE TO LOCAL STORAGE
# num_processes = 8
# image_folder_journal = journal_directory + '_images'
# isExist = os.path.exists(image_folder_journal)
# if not isExist:
#     os.makedirs(image_folder_journal)

# multiprocess_image_download_list = [{'application_number': app_num, 'local_folder': image_folder_journal} for app_num in journal_application_numbers]
# pool = Pool(num_processes)
# results = pool.map(multiprocess_download_image_from_azure_to_file, multiprocess_image_download_list)

# ### GENERATE IMAGE EMBEDDINGS FOR THE JOURNAL DATA
# journal_image_embedding_folder = image_folder_journal + '_embeddings'
# isExist = os.path.exists(journal_image_embedding_folder)
# if not isExist:
#     os.makedirs(journal_image_embedding_folder)

# image_paths = glob.glob(image_folder_journal + '/*')
# image_paths_split = int(len(image_paths)/num_processes)
# image_paths = [image_paths[index: index + image_paths_split] for index in range(0, len(image_paths), image_paths_split)]
# pool = Pool(num_processes)
# results = pool.map(generate_image_embedding, image_paths)
# journal_embeddings_path = glob.glob(journal_image_embedding_folder + '/*')
# journal_embedding_df_list = []
# for path in journal_embeddings_path:
#     journal_embedding_df_list.append(pd.read_csv(path, index_col=0, converters={'Embedding': pd.eval}))

# journal_embedding_df = pd.concat(journal_embedding_df_list).reset_index().drop('index', axis=1)

# ### GENERATE IMAGE SEARCH RESULTS 
# try:
#     chroma_client.delete_collection(name='visual_search')
#     collection = chroma_client.create_collection(name='visual_search')
# except:
#     collection = chroma_client.create_collection(name='visual_search')

# application_numbers_for_chroma = query_embedding_df['Application Number'].to_list() + journal_embedding_df['Application Number'].to_list() 
# embedding_list = query_embedding_df['Embedding'].to_list() + journal_embedding_df['Embedding'].to_list()
# embedding_array = np.array(embedding_list)
# pca = PCA(n_components=512)
# pca.fit(embedding_array)
# for index in range(512):
#     if sum(pca.explained_variance_ratio_[:index]) > 0.95:
#         threshold_pca = index

# transformed_embeddings = pca.transform(embedding_array)
# transformed_query_embeddings = [list(item) for item in transformed_embeddings[:len(query_embedding_df), :index]]
# transformed_journal_embeddings = [list(item) for item in transformed_embeddings[len(query_embedding_df):, :index]]
# journal_application_numbers_for_chroma = [str(item) for item in application_numbers_for_chroma[len(query_embedding_df):]]
# query_application_numbers_for_chroma = [str(item) for item in application_numbers_for_chroma[:len(query_embedding_df)]]
# collection.add(embeddings=transformed_journal_embeddings, ids=journal_application_numbers_for_chroma)
# image_search_results = collection.query(query_embeddings=transformed_query_embeddings, n_results=10)
# refined_image_search_results = refine_search_results(image_search_results, query_application_numbers_for_chroma)

### GENERATE TEXT-BASED SEARCH RESULTS
tm_collection = init_mongo_connection()
num_of_applications_to_process_at_a_time = 10000
query_data_list = []
for index in tqdm(range(0, len(all_query_application_numbers), num_of_applications_to_process_at_a_time)):
    query_data = mongo_application_search(tm_collection, all_query_application_numbers[index: index + num_of_applications_to_process_at_a_time])
    for data in query_data:
        query_data_list.append(data)

journal_data = mongo_application_search(tm_collection, journal_application_numbers)
journal_data_list = []
for data in journal_data:
    journal_data_list.append(data)

valid_journal_data = []
for index, data in enumerate(journal_data_list):
    if 'Publication Details' in data:
        try:
            if journal_directory in data['Publication Details']:
                valid_journal_data.append(data)
        except:
            continue

journal_to_be_scraped = []
for num in tqdm(journal_application_numbers):
    present = False
    for item in valid_journal_data:
        if num == item['Application Number']:
            present = True
    
    if not present:
        journal_to_be_scraped.append(num)


app_to_id_dict = {output['Application Number']: [] for output in valid_journal_data}
for output in valid_journal_data:
    app_num = output['Application Number']
    id_num = output['_id']
    app_to_id_dict[app_num].append(id_num)

update_operations_list = []
for record in valid_journal_data:
    application_number = record['Application Number']
    record['Journal Number'] = int(journal_directory)
    temp = record.copy()
    del temp['_id']
    # if len(app_to_id_dict[application_number]) == 1:
    update_operations_list.append(UpdateOne({'_id': app_to_id_dict[application_number][0]}, {'$set': temp}, upsert=True))
    # else:
    #     record['_id'] = app_to_id_dict[application_number][0]
    #     update_operations_list.append(UpdateOne({'_id': app_to_id_dict[application_number][0]}, {'$set': record}, upsert=True))


result = tm_collection.bulk_write(update_operations_list)

journal_df = pd.DataFrame.from_records(valid_journal_data).reset_index().drop('index', axis=1)
query_data_df = pd.DataFrame.from_records(query_data_list).reset_index().drop('index', axis=1)
query_mark_dict = generate_app_word_dict(query_data_df)
# candidate_apps, candidate_marks = generate_app_word_list(journal_df)
# candidate_apps_no_ignore, candidate_marks_no_ignore = generate_app_word_list_no_ignore(journal_df)
# text_search_results_remove = {}
# text_search_results_raw = {}
text_search_results = {}
for item in tqdm(valid_journal_data):
    journal_app = str(item['Application Number'])
    if 'Wordmark' in item:
        # text_search_results_remove[query_app] = fuzzy_search(item['Wordmark'], query_app, candidate_apps, candidate_marks, 10, remove=True)
        # text_search_results_raw[query_app] = fuzzy_search(item['Wordmark'], query_app, candidate_apps, candidate_marks, 10, remove=False)
        text_search_results[journal_app] = fuzzy_search_partial(item['Wordmark'], journal_app, query_mark_dict)


# for item in tqdm(query_data_list[:1000]):
#     query_app = str(item['Application Number'])
#     if 'Wordmark' in item:
#         # text_search_results_remove[query_app] = fuzzy_search(item['Wordmark'], query_app, candidate_apps, candidate_marks, 10, remove=True)
#         # text_search_results_raw[query_app] = fuzzy_search(item['Wordmark'], query_app, candidate_apps, candidate_marks, 10, remove=False)
#         text_search_results[query_app] = phonetic_text_search.fuzzy_search_partial(item['Wordmark'], query_app, journal_mark_dict)


### UPDATE MONGODB WITH JOURNAL CONFLICTS
journal_number = 2135
text_relevancy_threshold = 65.0
overall_accuracy = 0.0
# mongodb_new_data_remove = []
mongodb_new_data_raw = []
for index in tqdm(range(len(journal_df))):
    app_number = query_data_df.iloc[index]['Application Number']
    organizations = application_num_to_organization_dict[app_number]
    try:
        mongodb_new_data_raw += generate_pdf_reports.process_journal_conflict_record_journal_pov(journal_df.iloc[index], text_search_results, query_data_df, journal_number, organizations, text_relevancy_threshold, overall_accuracy)
        # mongodb_new_data_remove += process_journal_conflict_record(query_data_df.iloc[index], text_search_results_remove, journal_df, journal_number, organizations, text_relevancy_threshold, overall_accuracy)
    except:
        continue

for mongo_item in mongodb_new_data_raw:
    conflict_app_num = mongo_item['conflict_application_number']
    page_num = journal_page_dict[conflict_app_num]
    if len(page_num) == 1:
        mongo_item['Page Number'] = page_num[0]
    else:
        print('Conflict Application Number - ', conflict_app_num, page_num)
        mongo_item['Page Number'] = None

journal_conflict_collection = init_mongo_connection('journal-conflicts')
insert_at_a_time = 20000
for index in tqdm(range(0, len(mongodb_new_data_raw), insert_at_a_time)):
    update_database = journal_conflict_collection.insert_many(mongodb_new_data_raw[index: index + insert_at_a_time])


### GENERATE JOURNAL CONFLICT METADATA
class_categories = [[], [0], [1], [2], [0, 1], [0, 2], [1, 2], [0, 1, 2]]
risk_levels = [[75.0, 80.0], [80.0, 90.0], [90.0, 95.0], [95.0, 100.0]]
journal_numbers = [item for item in range(2135, 2136)]
organizations = ['RKDewan']
metadata = []
journal_conflict_collection = init_mongo_connection('journal-conflicts')
for org in organizations:
    for journal in journal_numbers:
        for risk in risk_levels:
            for category in class_categories:
                if category == []:
                    metadata.append({'Organization': org, 'Journal Number': journal, 'Min Risk': risk[0], 'Max Risk': risk[1], 'Class Categories': category, 'Count': 0})
                    continue
                output = journal_conflict_search(journal_conflict_collection, org, journal, risk[0], risk[1], category)
                count = [item for item in output][0]
                count = count['count']['total']
                metadata.append({'Organization': org, 'Journal Number': journal, 'Min Risk': risk[0], 'Max Risk': risk[1], 'Class Categories': category, 'Count': count})

journal_conflicts_metadata_collection = init_mongo_connection('journal-conflicts-metadata')
journal_conflicts_metadata_collection.insert_many(metadata)
### GENERATE EXCEL FILE FOR ORGANIZATION BASED ON RISK LEVEL SORTED DESCENDING
organization = "RKDewan"
risk_threshold = 80
filename = f"{organization}_2126.xlsx"
results_df = pd.DataFrame.from_records(mongodb_new_data_raw)
results_df = results_df[results_df['organization']==organization]
results_df = results_df[results_df['risk_level'] >= risk_threshold]
if '_id' in results_df.columns:
    results_df = results_df.drop(['_id'], axis=1)

results_df = results_df.drop(['class_category', 'organization'], axis=1)
results_df = results_df.sort_values(by='risk_level', ascending=False)
results_df = results_df.drop_duplicates().reset_index().drop('index', axis=1)
results_df.to_excel(filename)

### GENERATE PDF REPORTS
report_output_folder = '/Volumes/Seagate Backup Plus Drive/' + journal_directory + '_reports'
journal_number = 2126
query_image_folder = 'vs_images'
image_folder_journal = journal_directory + '_images'
isExist = os.path.exists(report_output_folder)
if not isExist:
    os.makedirs(report_output_folder)

very_high_subdirectory = report_output_folder + '/very_high'
high_subdirectory = report_output_folder + '/high'
moderate_subdirectory = report_output_folder + '/moderate'
low_subdirectory = report_output_folder + '/low'
if not isExist:
    os.makedirs(very_high_subdirectory)

if not isExist:
    os.makedirs(high_subdirectory)

if not isExist:
    os.makedirs(moderate_subdirectory)

if not isExist:
    os.makedirs(low_subdirectory)

query_data_df = pd.DataFrame.from_records(query_data_list)
print("Generating reports!")
image_relevancy_threshold = 10.0
text_relevancy_threshold = 65.0
for index in tqdm(range(len(query_data_df))):
    process_report(query_data_df.iloc[index], text_search_results, journal_df, journal_number, report_output_folder, image_folder_journal, query_image_folder, text_relevancy_threshold)

output_df_list = []
for index in tqdm(range(len(query_data_df))):
    output_df_list += generate_match_excel_list(query_data_df.iloc[index], text_search_results, journal_df)