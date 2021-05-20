import json
import requests
import pandas as pd,os,numpy as np
from tqdm import tqdm
from collections import Counter
import boto3
import datetime

BASIS_URL = "https://classes.cornell.edu/api/2.0/"

METHODS = ["config/rosters","config/acadCareers","config/acadGroups","config/classLevels","config/subjects","search/classes"]
METHODS_ARG = ["","roster","roster","roster,subject","roster,subject,acadCareer,classLevels","roster,subject,crseAttrs"]
STD_FORMAT = ".json"

class Roster():
    def __init__(self,ROSTER_PERIOD='SP21',part="1"):
        self.course_json = self.basic_json_extractor(method=METHODS[0],parameters=None)
        self.available_years_dict = self.available_rosters(self.course_json)
        self.subjects_json = self.basic_json_extractor(method=METHODS[4],parameters=ROSTER_PERIOD)['data']['subjects']
        self.ROSTER_PERIOD=ROSTER_PERIOD
        self.part=part


    def basic_json_extractor(self,method="config/rosters",parameters=None):
        """
        Input:
            method: str API method
            parameters: str or list for API method
        Output:
            extracted json

        From API descrip: https://<HOST>/api/<VERSION>/<method>.<responseFormat>?parameters
        https://<HOST>/api/<VERSION>/ is found in global variable BASIS_URL
        <responseFormat> is found in global variable STD_FORMAT
        """
        if type(parameters) == str:
            request = requests.get(BASIS_URL+method+STD_FORMAT+"?roster="+parameters)
        elif type(parameters) == list:
            arg = "?roster="+parameters[0]+"&subject="+parameters[1] #terrible code I know. I will fix later -Mads
            request = requests.get(BASIS_URL + method + STD_FORMAT + arg)
        else:
            request = requests.get(BASIS_URL + method + STD_FORMAT)
        json = request.json()
        return json

    def available_rosters(self,course_json):
        """
        Input:
            course_json: Response (standard requests.get(link), where link is .../config/rosters.json)
        Output:
            Dictionary with roster as key (ex. FA15), and idx as value
        """
        years = [(course_json['data']['rosters'][idx]['slug'], idx) for idx, year in
                 enumerate(range(len(course_json['data']['rosters'])))]
        return dict(years)

    def extract_course_rosterv0(self):
        test_subject = self.subjects_json[48]['value'] #Computer science
        classes = self.basic_json_extractor(method=METHODS[5],parameters=[self.ROSTER_PERIOD,test_subject])
        data = classes['data']['classes']
        dataFrame = pd.DataFrame.from_dict(data)
        a = 2
        return 0

    def recursive_detangling(self,entangled):
        still_needs_untangling = []
        keys_for_untangling = []
        for key, value in entangled.items():
            if isinstance(value, list):
                if len(value) > 0:
                    if isinstance(value[0], dict):
                        keys_for_untangling.append(key)
                    elif len(value) ==1:
                        entangled[key] = value[0]


        for key in keys_for_untangling:
            still_needs_untangling.append(entangled.pop(key))

        detangled = pd.DataFrame.from_dict(entangled,orient='index').T

        for item in still_needs_untangling:
            new_detangled = self.recursive_detangling(item[0])
            detangled_column_set = set(detangled.columns)
            if not any([col in detangled_column_set for col in new_detangled.columns]):
                detangled = pd.concat([detangled,new_detangled],axis=1) #, join="inner"
            else:
                duplicates = new_detangled.columns[[col in detangled_column_set for col in new_detangled.columns]]
                for duplicate in duplicates:
                    new_detangled.rename(columns={duplicate: duplicate+"_copy"},inplace=True)
                detangled = pd.concat([detangled,new_detangled],axis=1) #, join="inner"



        return detangled
    def extract_course_rosterv1(self,subject=None):
        year = self.ROSTER_PERIOD
        if type(subject) == type(None):
            num_sub = round(len(self.subjects_json)/2)
            if self.part=="1":
                subset = self.subjects_json[:num_sub]
            else:
                subset = self.subjects_json[num_sub:]
            for i in tqdm(range(len(subset))):
                temp_sub = subset[i]['value']
                classes = self.basic_json_extractor(method=METHODS[5], parameters=[year, temp_sub])
                temp_data = classes['data']['classes']
                detangled_column = pd.DataFrame()
                for j in range(len(classes['data']['classes'])):
                    if j == 0:
                        detangled_column = self.recursive_detangling(classes['data']['classes'][j]['enrollGroups'][0])
                    else:
                        temp = self.recursive_detangling(classes['data']['classes'][j]['enrollGroups'][0])
                        detangled_column = pd.concat([detangled_column,temp])

                temp_column = pd.DataFrame.from_dict(detangled_column)
                temp_dataFrame = pd.DataFrame.from_dict(temp_data)
                temp_column.set_index(temp_dataFrame.index,inplace=True)

                temp_dataFrame_set = set(temp_dataFrame)
                duplicates = temp_column.columns[[col in temp_dataFrame_set for col in temp_column.columns]]
                for duplicate in duplicates:
                    temp_column.rename(columns={duplicate: duplicate + "_copy"}, inplace=True)

                temp_dataFrame = pd.concat([temp_dataFrame, temp_column], axis=1)
                if i == 0:
                    df = temp_dataFrame
                else:
                    #remove duplicates:
                    duplicates = [(category, count)  for category,count in Counter(temp_dataFrame).items() if count > 1]

                    df = pd.concat([df, temp_dataFrame], axis=0)
        else:
            classes = self.basic_json_extractor(method=METHODS[5], parameters=[self.ROSTER_PERIOD, subject])
            data = classes['data']['classes']
            dataFrame = pd.DataFrame.from_dict(data)

        return df
    def add_our_id(self, data):
        course_dict = dict()

        new_json_file = ""
        '''append new dictionary field "ourID" to current dictionary
            that accounts for any cross-listed classes
        '''
        for i in range(0,len(data)):
            i_title = data[i]['titleLong']
            i_desc = data[i]['description']
            i_crseId = data[i]['crseId']
            key = (i_title, i_desc)

            if (key in course_dict.keys()):
                data[i]['ourId'] = course_dict[key]

            else:
                data[i]['ourId'] = i_crseId
                course_dict[key] = i_crseId
        return data


def lambda_handler(event, context):
    current_month = datetime.datetime.now().month
    current_year = datetime.datetime.now().year
    part = event['part']

    bucket_name = "cornell-course-data-bucket"
    s3 = boto3.resource("s3")
    
    term = ''
    if (current_month > 1 and current_month < 6):
        term+="FA"+str(datetime.datetime.now().year)[2:]
    else:
        term+="SP"+str(datetime.datetime.now().year+1)[2:]

    if part == "3": # Combining parts 1 and 2
        pt1 = "course_data_"+term+"_pt1.json"
        pt2 = "course_data_"+term+"_pt2.json"

        content_object1 = s3.Object(bucket_name, pt1)
        file_content1 = content_object1.get()['Body'].read().decode('utf-8')
        json_content1 = json.loads(file_content1)
        content_object2 = s3.Object(bucket_name, pt2)
        file_content2 = content_object2.get()['Body'].read().decode('utf-8')
        json_content2 = json.loads(file_content2)
        both = json_content1+json_content2
        both = json.dumps(both)
        encoded_string = both.encode("utf-8")
        file_name = "course_data_"+term+".json"
        s3.Bucket(bucket_name).put_object(Key=file_name, Body=encoded_string, ACL='public-read')

    else:

        file_name = "course_data_"+term+"_pt"+part+".json"

        roster = Roster(term, part)
        data = roster.extract_course_rosterv1()
        data = data.reset_index()

        json_data = json.loads(data.to_json(orient="records"))

        json_data = roster.add_our_id(json_data)
        string = json.dumps(json_data)

        encoded_string = string.encode("utf-8")
        s3.Bucket(bucket_name).put_object(Key=file_name, Body=encoded_string, ACL='public-read')

