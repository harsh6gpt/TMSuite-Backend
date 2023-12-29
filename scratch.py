import os
import pandas as pd
from generate_pdf_reports import map_score, related_classes
from rapidfuzz import fuzz


def generate_risk_excel(report_folder, csv_output_name):
    very_high_apps = [{'Application Number': item.split('.')[0], 'Risk': 'very_high'} for item in os.listdir(f'{report_folder}/very_high/')]
    high_apps = [{'Application Number': item.split('.')[0], 'Risk': 'high'} for item in os.listdir(f'{report_folder}/high/')]
    moderate_apps = [{'Application Number': item.split('.')[0], 'Risk': 'moderate'} for item in os.listdir(f'{report_folder}/moderate/')]
    low_apps = [{'Application Number': item.split('.')[0], 'Risk': 'low'} for item in os.listdir(f'{report_folder}/low/')]
    all_apps = very_high_apps + high_apps + moderate_apps + low_apps
    df = pd.DataFrame.from_records(all_apps)
    df.to_csv(csv_output_name)
    return


def generate_match_excel_list(query_mark_details, search_results, journal_df):
    application_number = query_mark_details['Application Number']
    class_number = query_mark_details['Class']
    search_results = search_results[f'{application_number}']
    output_list = []
    if search_results:
        for result in search_results:
            result_app_number = result[0]
            result_score = result[1]
            result_details = journal_df[journal_df['Application Number'] == result_app_number].to_dict(orient='records')[0]
            if result_details['Class'] == class_number:
                result_score = result_score + 10.0
                result_score = map_score(result_score)
            elif result_details['Class'] in related_classes[class_number]:
                result_score = result_score + 6.0
                if result_score >= 90.0 and result_score < 100.0:
                    result_score = 90.0 + (result_score - 90.0)/2.0
                elif result_score >= 100.0:
                    result_score = 95.0 + (result_score - 100.0)/1.2
                else:
                    result_score = result_score
            else:
                result_score = result_score * 0.94
            if result_score < 90.0:
                continue
            elif fuzz.QRatio(query_mark_details['Wordmark'], result_details['Wordmark']) < 75.0:
                continue
            elif fuzz.QRatio(query_mark_details['Proprietor name'], result_details['Proprietor name']) > 95.0:
                continue
            else:
                output_dict = {'Query Mark Application Number': application_number, 'Query Mark Class': class_number, 
                'Query Mark': query_mark_details['TM Applied For'], 'Query Proprietor': query_mark_details['Proprietor name'], 
                'Result Mark Application Number': result_details['Application Number'], 'Result Mark Class': result_details['Class'],
                'Result Mark': result_details['TM Applied For'], 'Score': result_score, 'Result Proprietor': result_details['Proprietor name']}
                output_list.append(output_dict)
        return output_list
    else:
        return output_list
