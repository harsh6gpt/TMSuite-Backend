from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus.flowables import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
import numpy as np
import pandas as pd
import glob
from PIL import Image as PILImage
from rapidfuzz import fuzz


def map_score(score):
    if score >= 90.0 and score < 100.0:
        score = 90.0 + (score - 90.0)/2.0
    elif score >= 100.0:
        score = 95.0 + (score - 100.0)/2.0
    else:
        score = score
    return score


related_classes = {9: [42], 42: [9], 5: [3, 5, 10, 44], 41: [16, 28], 25: [22, 23, 24, 25], 35: [], 30: [29, 31, 32, 43], 43: [], 3: [5, 10, 44], 29: [30, 31, 32, 43], 
                   44: [1, 3, 5, 10], 36: [37], 21: [20, 22, 11], 11: [9, 12, 21], 31: [29, 30, 31, 32, 43], 14: [6, 9], 39: [42, 12, 16], 20: [21, 22], 37: [36, 6, 7, 11, 9], 
                   18: [], 16: [], 32: [29, 30, 31, 33, 43], 45: [44, 41, 10], 28: [9, 13, 41], 24: [], 10: [3, 5, 44], 7: [6, 11, 12, 37, 40], 1: [2, 4, 9, 19], 12: [], 
                   19: [], 6: [7, 11, 12, 37, 40], 38: [42], 17: [19, 1], 4: [1, 7, 12], 40: [1, 6], 2: [], 8: [7, 6, 21], 34: [], 27: [], 26: [23, 24, 25], 33: [32, 43], 
                   22: [23, 24, 26], 15: [], 23: [24, 25], 13: [], 99: []}


class FooterCanvas(canvas.Canvas):

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_canvas(page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_canvas(self, page_count):
        marketing = "Report generated using TMEagle by LegalGita."
        page = "Page %s of %s" % (self._pageNumber, page_count)
        x_marketing = 544
        x_page = 112
        self.saveState()
        self.setStrokeColorRGB(0, 0, 0)
        self.setLineWidth(0.5)
        self.line(66, 78, LETTER[0] - 66, 78)
        self.setFont('Times-Roman', 10)
        self.drawString(LETTER[0]-x_page, 65, page)
        self.drawString(LETTER[0]-x_marketing, 65, marketing)
        self.restoreState()


# Create a function to generate a PDF for a single trademark
def generate_trademark_pdf(pdf_filename, output_folder, query_trademark, trademark_data, journal_number, journal_images_folder, query_images_folder):
    score = trademark_data[0][1]
    if score >= 75.0 and score <80.0:
        output_path = f'{output_folder}/low/{pdf_filename}.pdf'
    elif score >= 80.0 and score < 90.0:
        output_path = f'{output_folder}/moderate/{pdf_filename}.pdf'
    elif score >= 90.0 and score < 95.0:
        output_path = f'{output_folder}/high/{pdf_filename}.pdf'
    else:
        output_path = f'{output_folder}/very_high/{pdf_filename}.pdf'

    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Add your company logo
    logo = "zolvit.png"
    elements.append(Image(logo, width=3*inch, height=1.5*inch))
    elements.append(Spacer(1, 0.5*inch))
    
    # Add a title
    title_style = styles["Heading1"]
    elements.append(Paragraph(f"Trademark Similarity Report for Journal {journal_number}", title_style))
    elements.append(Spacer(1, 0.2*inch))

    subtitle_style = styles["Heading2"]
    elements.append(Paragraph(f"Your Trademark:", subtitle_style))
    elements.append(Spacer(1, 0.2*inch))
    
    table_data = []
    query_app = query_trademark['Application Number']
    query_images = glob.glob(f'{query_images_folder}/{query_app}*')
    if query_images:
        try:
            image_check = PILImage.open(query_images[0])
            table_data.append(['Application Number', query_trademark['Application Number'], Image(query_images[0], width=1*inch, height=1*inch)])
        except:
            table_data.append(['Application Number', query_trademark['Application Number'], 'No Image Available'])
    else:
        table_data.append(['Application Number', query_trademark['Application Number'], 'No Image Available'])
    try:
        query_mark = query_trademark['TM Applied For']
    except:
        query_mark = 'Not Available'
    if len(query_mark) > 20:
        table_data.append(['Wordmark', Paragraph(query_mark), ''])
    else:
        table_data.append(['Wordmark', query_mark, ''])
    try:
        query_class = query_trademark['Class']
    except:
        query_class = 'Not Available'
    table_data.append(['Class', query_class, ''])

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (1, 0), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (2, 0), (2, -1))# Center-align vertically in cells
    ])

    # Define column widths for text data and image
    col_widths = [2*inch, 2*inch, 2*inch]

    trademark_table = Table(table_data, style=table_style, colWidths=col_widths)
    elements.append(trademark_table)
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(f"Similar Trademarks Found:", subtitle_style))
    elements.append(Spacer(1, 0.2*inch))

    for trademark in trademark_data:
        # Create a table for trademark data
        score = trademark[1]
        trademark = trademark[0]
        table_data = []
        tm_app_number = trademark['Application Number']
        tm_images = glob.glob(f'{journal_images_folder}/{tm_app_number}*')
        if tm_images:
            try:
                image_check = PILImage.open(tm_images[0])
                table_data.append(['Application Number', trademark['Application Number'], Image(tm_images[0], width=1*inch, height=1*inch)])
            except:
                table_data.append(['Application Number', trademark['Application Number'], 'No Image Available'])
        else:
            table_data.append(['Application Number', trademark['Application Number'], 'No Image Available'])
        try:
            tm_mark = trademark['TM Applied For']
        except:
            tm_mark = 'Not Available'
        if len(tm_mark) > 20:
            table_data.append(['Wordmark', Paragraph(tm_mark), ''])
        else:
            table_data.append(['Wordmark', tm_mark, ''])
        try:
            tm_class = trademark['Class']
        except:
            tm_class = 'Not Available'
        table_data.append(['Class', tm_class, ''])
        score = int(round(score))
        if score >= 75.0 and score <80.0:
            risk_level = f'{score}%, LOW'
        elif score >= 80.0 and score < 90.0:
            risk_level = f'{score}%, MODERATE'
        elif score >= 90.0 and score < 95.0:
            risk_level = f'{score}%, HIGH'
        else:
            risk_level = f'{score}%, VERY HIGH'
        table_data.append(['Risk Level', risk_level, ''])
        try:
            tm_use = trademark['Used Since']
            if tm_use is pd.NaT or str(tm_use) == 'nan':
                tm_use = 'Not Available'
        except:
            tm_use = 'Not Available'
        table_data.append(['Date of Use', tm_use, ''])
        try:
            tm_goods_details = str(trademark['Goods & Service Details'])
            if tm_goods_details is None or tm_goods_details is pd.NaT or str(tm_goods_details) == 'nan':
                tm_goods_details = 'Not Available'
        except:
            tm_goods_details = 'Not Available'
        if len(tm_goods_details) > 20:
            table_data.append(['Nature of Business', Paragraph(tm_goods_details[:100]), ''])
        else:
            table_data.append(['Nature of Business', tm_goods_details, ''])
        try:
            tm_proprietor = str(trademark['Proprietor name'])
            if tm_proprietor is None or tm_proprietor is pd.NaT:
                tm_proprietor = 'Not Available'
        except:
            tm_proprietor = 'Not Available'
        if len(tm_proprietor) > 20:
            table_data.append(['Proprietor Name', Paragraph(tm_proprietor[:100]), ''])
        else:
            table_data.append(['Proprietor Name', tm_proprietor, ''])
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (1, 0), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('SPAN', (2, 0), (2, -1))# Center-align vertically in cells
        ])

        # Define column widths for text data and image
        col_widths = [2*inch, 2*inch, 2*inch]

        trademark_table = Table(table_data, style=table_style, colWidths=col_widths)
        elements.append(trademark_table)
        elements.append(Spacer(1, 0.4*inch))

    # Build the PDF document
    doc.multiBuild(elements, canvasmaker=FooterCanvas)


# Generate PDF for the trademarks
def process_report(query_mark_details, search_results, journal_df, journal_number, output_folder, journal_images_folder, query_images_folder, text_relevancy_threshold = 65.0):
    application_number = query_mark_details['Application Number']
    class_number = query_mark_details['Class']
    search_results = search_results[f'{application_number}']
    output_list = []
    output_score = []
    for result in search_results:
        if result[1] < text_relevancy_threshold:
            break
        else:
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
            if result_score < text_relevancy_threshold + 10.0:
                continue
            elif fuzz.QRatio(query_mark_details['Wordmark'], result_details['Wordmark']) < 60.0:
                continue
            elif fuzz.QRatio(query_mark_details['Proprietor name'], result_details['Proprietor name']) > 95.0:
                continue
            else:
                output_list.append((result_details, result_score))
                output_score.append(-1*result_score)
    sorted_indices = np.argsort(output_score)
    if output_list:
        final_output = [output_list[index] for index in sorted_indices]
        generate_trademark_pdf(application_number, output_folder, query_mark_details, final_output, journal_number, journal_images_folder, query_images_folder)
    return


def process_journal_conflict_record(query_mark_details, search_results, journal_df, journal_number, organizations, text_relevancy_threshold = 65.0, overall_accuracy = 65.0):
    application_number = query_mark_details['Application Number']
    class_number = query_mark_details['Class']
    search_results = search_results[f'{application_number}']
    output_list = []
    for result in search_results:
        if result[1] < text_relevancy_threshold:
            break
        else:
            result_app_number = result[0]
            result_score = result[1]
            result_details = journal_df[journal_df['Application Number'] == result_app_number].to_dict(orient='records')[0]
            if result_details['Class'] == class_number:
                result_score = result_score + 10.0
                result_score = map_score(result_score)
                result_class_category = 0
            elif result_details['Class'] in related_classes[class_number]:
                result_score = result_score + 6.0
                if result_score >= 90.0 and result_score < 100.0:
                    result_score = 90.0 + (result_score - 90.0)/2.0
                elif result_score >= 100.0:
                    result_score = 95.0 + (result_score - 100.0)/1.2
                else:
                    result_score = result_score
                result_class_category = 1
            else:
                result_score = result_score * 0.94
                result_class_category = 2
            if result_score < text_relevancy_threshold + 10.0:
                continue
            elif fuzz.QRatio(query_mark_details['Wordmark'], result_details['Wordmark']) < overall_accuracy:
                continue
            elif fuzz.QRatio(query_mark_details['Proprietor name'], result_details['Proprietor name']) > 95.0:
                continue
            else:
                for organization in organizations:
                    result_dict = {}
                    result_dict['query_application_number'] = int(result_details['Application Number'])
                    result_dict['query_class'] = int(result_details['Class']) 
                    result_dict['query_mark'] = result_details['TM Applied For']
                    result_dict['conflict_application_number'] = int(application_number)
                    result_dict['conflict_class'] = int(class_number)
                    result_dict['conflict_mark'] = query_mark_details['TM Applied For'] 
                    result_dict['conflict_proprietor_name'] = query_mark_details['Proprietor name']
                    result_dict['conflict_date_of_application'] = query_mark_details['Date of Application']
                    if query_mark_details['Used Since'] is pd.NaT:
                        query_mark_details['Used Since'] = None
                    result_dict['conflict_used_since'] = query_mark_details['Used Since']
                    result_dict['conflict_goods_services'] = query_mark_details['Goods & Service Details']
                    result_dict['risk_level'] = int(round(result_score))
                    result_dict['journal_number'] = int(journal_number)
                    result_dict['organization'] = organization
                    result_dict['class_category'] = result_class_category
                    output_list.append(result_dict)
    return output_list


def process_journal_conflict_record_journal_pov(journal_mark_details, search_results, query_df, journal_number, organizations, text_relevancy_threshold = 65.0, overall_accuracy = 65.0):
    application_number = journal_mark_details['Application Number']
    class_number = journal_mark_details['Class']
    search_results = search_results[f'{application_number}']
    output_list = []
    for result in search_results:
        if result[1] < text_relevancy_threshold:
            break
        else:
            result_app_number = result[0]
            result_score = result[1]
            result_details = query_df[query_df['Application Number'] == result_app_number].to_dict(orient='records')[0]
            if result_details['Class'] == class_number:
                result_score = result_score + 10.0
                result_score = map_score(result_score)
                result_class_category = 0
            elif result_details['Class'] in related_classes[class_number]:
                result_score = result_score + 6.0
                if result_score >= 90.0 and result_score < 100.0:
                    result_score = 90.0 + (result_score - 90.0)/2.0
                elif result_score >= 100.0:
                    result_score = 95.0 + (result_score - 100.0)/1.2
                else:
                    result_score = result_score
                result_class_category = 1
            else:
                result_score = result_score * 0.94
                result_class_category = 2
            if result_score < text_relevancy_threshold + 10.0:
                continue
            elif fuzz.QRatio(journal_mark_details['Wordmark'], result_details['Wordmark']) < overall_accuracy:
                continue
            elif fuzz.QRatio(journal_mark_details['Proprietor name'], result_details['Proprietor name']) > 95.0:
                continue
            else:
                for organization in organizations:
                    result_dict = {}
                    result_dict['query_application_number'] = int(result_details['Application Number'])
                    result_dict['query_class'] = int(result_details['Class']) 
                    result_dict['query_mark'] = result_details['TM Applied For']
                    result_dict['query_proprietor_name'] = result_details['Proprietor name']
                    result_dict['query_date_of_application'] = result_details['Date of Application']
                    if result_details['Used Since'] is pd.NaT:
                        result_details['Used Since'] = None
                    result_dict['query_used_since'] = result_details['Used Since']
                    result_dict['query_status'] = result_details['tm_status']
                    result_dict['query_goods_services'] = result_details['Goods & Service Details']
                    result_dict['conflict_application_number'] = int(application_number)
                    result_dict['conflict_class'] = int(class_number)
                    result_dict['conflict_mark'] = journal_mark_details['TM Applied For'] 
                    result_dict['conflict_proprietor_name'] = journal_mark_details['Proprietor name']
                    result_dict['conflict_proprietor_address'] = journal_mark_details['Proprietor Address']
                    result_dict['conflict_attorney_name'] = journal_mark_details['Attorney name']
                    result_dict['conflict_agent_name'] = journal_mark_details['Agent name']
                    result_dict['conflict_date_of_application'] = journal_mark_details['Date of Application']
                    if journal_mark_details['Used Since'] is pd.NaT:
                        journal_mark_details['Used Since'] = None
                    result_dict['conflict_used_since'] = journal_mark_details['Used Since']
                    result_dict['conflict_goods_services'] = journal_mark_details['Goods & Service Details']
                    result_dict['risk_level'] = int(round(result_score))
                    result_dict['journal_number'] = int(journal_number)
                    result_dict['organization'] = organization
                    result_dict['class_category'] = result_class_category
                    output_list.append(result_dict)
    return output_list
