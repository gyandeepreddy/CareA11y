import os
import boto3
from dotenv import load_dotenv
from region_lookup import active_region

load_dotenv()


def aws_api_client(service_name):
    return boto3.client(service_name=service_name, region_name=active_region())


# text = "PERCUTANEOUS CARDIOVASCULAR PROCEDURES WITHOUT ACUTE MYOCARDIAL INFARCTION, WITHOUT CORONARY ARTERY STENT IMPLANT"
# result = api_client("comprehendmedical").detect_entities(Text= text)
# print(result)
