from phonetics import metaphone, soundex
from rapidfuzz import process, fuzz
import math

ignore_list = ['device', 'label', 'logo', 'logo with device', 'with device', 'miscellaneous device']
transform_list = [{'word': ' enterprise', 'pick': 0}, {'word': 'with device', 'pick': 0}, {'word': 'device of', 'pick': 1}, {'word': '(device)', 'pick': 0},
                  {'word': ' infotech', 'pick': 0}, {'word': ' developer', 'pick': 0}, {'word': ' construction', 'pick': 0}, {'word': ' pharmaceutical', 'pick': 0}, 
                  {'word': ' healthcare', 'pick': 0}, {'word': ' hotel', 'pick': 0}, {'word': ' fashion', 'pick': 0}, {'word': ' craft', 'pick': 0}, {'word': ' publication', 'pick': 0},
                  {'word': ' international', 'pick': 0}, {'word': ' studio', 'pick': 0}, {'word': ' makeup', 'pick': 0}, {'word': ' tour', 'pick': 0}, {'word': ' travel', 'pick': 0}, 
                  {'word': ' company', 'pick': 0}, {'word': ' technologies', 'pick': 0}, {'word': ' charitable', 'pick': 0}, {'word': ' production', 'pick': 0}, {'word': ' solution', 'pick': 0},
                  {'word': ' coaching', 'pick': 0}, {'word': ' center', 'pick': 0}, {'word': ' centre', 'pick': 0}, {'word': ' engineering', 'pick': 0}, {'word': ' jewellers', 'pick': 0}, 
                  {'word': ' fantasy', 'pick': 0}]


remove_word_list = []
with open(r'ignore_refined.txt', 'r') as fp:
    for line in fp:
        word = line[:-1]
        remove_word_list.append(word)
     

def transform_list_word_occurence(word):
    output = []
    for item in transform_list:
        if item['word'] in word.strip():
            output.append(item['word'])
    return ",".join(output)


def transform_word(word):
    for item in transform_list:
        if item['word'] in word.strip():
            word = word.strip().split(item['word'])[item['pick']].strip()
    return word


def remove_words(word):
    word_list = word.split(' ')
    word_list = [item.strip() for item in word_list]
    new_word_list = []
    count = 0
    for index, item in enumerate(word_list):
        if count > 1:
            break
        if item in remove_word_list:
            continue
        else:
            new_word_list.append(item)
            count += 1
    return " ".join(new_word_list).strip()


def generate_app_word_dict(data_df, class_filter='ALL'):
    if class_filter != 'ALL':
        data_df = data_df[data_df['Class'].isin(class_filter)].reset_index()
    output_dict = {}
    for index in range(len(data_df)):
        application_number = int(data_df.iloc[index]['Application Number'])
        wordmark = data_df.iloc[index]['Wordmark']
        try:
            if math.isnan(wordmark):
                output_dict[application_number] = ["", ""]
        except:
            wordmark = str(wordmark.strip())
            if wordmark in ignore_list:
                output_dict[application_number] = ["", ""]
            else:
                output_dict[application_number] = [wordmark]
                processed_wordmark = remove_words(wordmark)
                if processed_wordmark == "" or processed_wordmark == " " or len(processed_wordmark) == 1:
                    output_dict[application_number].append("")
                else:
                    output_dict[application_number].append(processed_wordmark)
    return output_dict


def generate_app_word_list(data_df, class_filter='ALL'):
    if class_filter != 'ALL':
        data_df = data_df[data_df['Class'].isin(class_filter)].reset_index()
    application_numbers = data_df['Application Number'].to_list()
    wordmarks = []
    application_numbers_output = []
    for index, item in enumerate(data_df['Wordmark'].to_list()):
        try:
            if math.isnan(item):
                continue
        except:
            mark = str(item)
            if mark.strip() not in ignore_list:
                temp = remove_words(mark)
                if temp != "" and temp != " ":
                    wordmarks.append(temp)
                    application_numbers_output.append(application_numbers[index])
    return application_numbers_output, wordmarks


def generate_app_word_list_no_ignore(data_df, class_filter='ALL'):
    if class_filter != 'ALL':
        data_df = data_df[data_df['Class'].isin(class_filter)].reset_index()
    application_numbers = data_df['Application Number'].to_list()
    wordmarks = []
    application_numbers_output = []
    for index, item in enumerate(data_df['Wordmark'].to_list()):
        try:
            if math.isnan(item):
                continue
        except:
            mark = str(item)
            if mark.strip() not in ignore_list:
                temp = mark.strip()
                if temp != "" and temp != " ":
                    wordmarks.append(mark.strip())
                    application_numbers_output.append(application_numbers[index])
    return application_numbers_output, wordmarks


def generate_phonetic_marks_list(data_df, class_filter='ALL', transform_type='soundex'):
    if class_filter != 'ALL':
        data_df = data_df[data_df['Class'].isin(class_filter)].reset_index()
    application_numbers = data_df['Application Number'].to_list()
    wordmarks = [str(item) for item in data_df['Wordmark'].to_list()]
    phonetic_marks = []
    relevant_indices = []
    for index, mark in enumerate(wordmarks):
        if mark.strip() not in ignore_list:
            try:
                if transform_type == 'metaphone':
                    phonetic_mark = metaphone(transform_word(wordmarks[index]))
                else:
                    phonetic_mark = soundex(transform_word(wordmarks[index]))
                phonetic_marks.append(phonetic_mark)
                relevant_indices.append(index)
            except:
                continue
    application_numbers = [application_numbers[index] for index in relevant_indices]
    return application_numbers, phonetic_marks

    
def phonetic_search(query_word, query_app, application_numbers, phonetic_marks, search_type='soundex', num_results=10):
    if query_word.strip() in ignore_list:
        return []
    if search_type=='metaphone':
        try:
            results = process.extract(metaphone(transform_word(query_word)), phonetic_marks, scorer=fuzz.QRatio, limit=num_results)
        except:
            return []
    else:
        try:
            results = process.extract(soundex(transform_word(query_word)), phonetic_marks, scorer=fuzz.QRatio, limit=num_results)
        except:
            return []
    result_output = [(application_numbers[item[2]], item[1]) for item in results]
    for item in result_output:
        if item[0] == query_app:
            result_output.remove(item)
    return result_output
    

def fuzzy_search(query_word, query_app, application_numbers, wordmarks, num_results=50, remove=True):
    if query_word.strip() in ignore_list:
        return []
    if remove:
        query_word_new = remove_words(query_word)
    else:
        query_word_new = query_word.strip()
    if len(query_word_new) == 1:
        return []
    results = process.extract(query_word_new, wordmarks, scorer=fuzz.QRatio, limit=num_results)
    result_output = [(application_numbers[item[2]], item[1]) for item in results]
    for item in result_output:
        if str(item[0]) == query_app:
            result_output.remove(item)
    return result_output


def process_results(results, query_mark, cutoff=75.0):
    new_results = []
    for item in results:
        split_conflict = item[0].split(' ')
        for split in split_conflict:
            if fuzz.ratio(split, query_mark) >= cutoff:
                new_results.append(item)
                break
    return new_results


def fuzzy_search_partial(query_mark, query_app, journal_mark_dict, num_results=300):
    journal_mark_dict_keys = list(journal_mark_dict.keys())
    query_mark = query_mark.strip()
    query_mark_split = remove_words(query_mark).split(' ')
    if query_mark in ignore_list:
        return []
    else:    
        if len(query_mark_split) == 1:
            if len(query_mark_split[0]) == 1:
                return []
        wordmarks = [journal_mark_dict[mark][1] for mark in journal_mark_dict]
        results = []
        for split in query_mark_split:
            if len(split) <= 1:
                continue
            results_split = process.extract(split, wordmarks, scorer=fuzz.partial_ratio, limit=num_results)
            results_split = process_results(results_split, split)
            results += results_split
            
        result_output = [(journal_mark_dict_keys[item[2]], item[1]) for item in results]

        # results = process.extract(query_mark, wordmarks, scorer=fuzz.partial_ratio, limit=num_results)
        # results = process_results(results, query_mark)
        # result_output = [(journal_mark_dict_keys[item[2]], item[1]) for item in results]
        # for key in journal_mark_dict_keys:
        #     if len(journal_mark_dict[key][0].split(' ')) == 1 or journal_mark_dict[key][1] == "":
        #         wordmarks.append(journal_mark_dict[key][0])
        #     else:
        #         wordmarks.append(journal_mark_dict[key][1])


    for item in result_output:
        if str(item[0]) == query_app:
            result_output.remove(item)

    result_output = sorted(result_output, key=lambda x: x[1], reverse=True)
    final_output = []
    for item in result_output:
        if item[1] > 80.0:
            final_output.append(item)
    return final_output

 