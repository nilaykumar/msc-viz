#!/usr/bin/env python3

import requests
import time
import xml.etree.ElementTree as ET

def harvest(date_from = '2020-01-01', serial = 'Advances in Mathematics', out_file = 'data.csv', rt = ''):
    csv_header = 'id,serial,pub,class,refclass\n'
    with open(out_file, 'a' if rt else 'w') as f:
        # write column names if starting a new file
        if not rt:
            f.write(csv_header)
        # construct initial query
        query = f'https://oai.zbmath.org/v1/?verb=ListRecords&from={date_from}&metadataPrefix=oai_zb_preview'
        while True:
            #timer_start = time.perf_counter()
            r = requests.get(query + ('&resumptionToken=' + rt if rt else ''))
            #timer_request = time.perf_counter()
            #print(f'Time[request]:\t {timer_request - timer_start:0.4f}')
            try:
                row, resumption = harvest_records(ET.fromstring(r.text), serial)
            except(Exception) as e:
                print('Error occured while parsing XML! Skipping this set of records...')
                continue
            #timer_harvest = time.perf_counter()
            #print(f'Time[harvest]:\t {timer_harvest - timer_request:0.4f}')
            f.write(row)
            #timer_write = time.perf_counter()
            #print(f'Time[write]:\t {timer_write - timer_harvest:0.4f}')
            if resumption is None:
                break
            rt = resumption.text
            cursor = resumption.attrib["cursor"]
            list_size = resumption.attrib["completeListSize"]
            complete = int(cursor) / int(list_size)
            print(f'{cursor} / {list_size} = {complete * 100:.2f}% \t {rt}')
        print('...done!')


def harvest_records(root, target_serial):
    invalid_marker = 'zbMATH'
    # allow omitting namespace for the default namespace
    ns = {'': 'http://www.openarchives.org/OAI/2.0/',
          'zbmath': 'https://zbmath.org/zbmath/elements/1.0/'}

    # get the list of returned records
    records = root.findall('./ListRecords/record', ns)
    resumption = root.find('./ListRecords/resumptionToken', ns)
    csv_string = ''
    for record in records:
        oai_zb_preview = record.find('./metadata//', ns)
        # make sure there's a serial tag
        if not oai_zb_preview.findall('./zbmath:serial/', ns):
            continue
        serial = oai_zb_preview.find('./zbmath:serial/zbmath:serial_title', ns).text
        # remove any unnecessary whitespace from the serial name
        serial = ' '.join(serial.strip().split())
        # restrict ourselves to the targeted serial
        if serial != target_serial:
            continue
        references_element = oai_zb_preview.find('./zbmath:references', ns)
        # if no references are provided, drop the record
        if references_element is None or invalid_marker in references_element.text:
            continue
        references = references_element.findall('./zbmath:reference', ns)
        # we allow duplicates because we might be interesting in seeing
        # which reference MSCs are overrepresented
        ref_classifications = []
        for reference in references:
            ref_classifications += [element.text.strip() for element in reference.findall('./zbmath:ref_classifications/zbmath:ref_classification', ns)]
        # if no reference MSCs are provided
        if not ref_classifications:
            continue
        document_id = oai_zb_preview.find('./zbmath:document_id', ns).text
        publication_year = oai_zb_preview.find('./zbmath:publication_year', ns).text
        classifications = [element.text for element in oai_zb_preview.findall('./zbmath:classifications/zbmath:classification', ns)]

        # we wrap the lists in double quotes due to the commas
        record_string = f'{document_id},{serial},{publication_year},"{classifications}","{sorted(ref_classifications)}"'
        csv_string += record_string + '\n'
    return csv_string, resumption

