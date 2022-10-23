import os
from dotenv import load_dotenv
from google.oauth2 import service_account
import googleapiclient.discovery

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

BASE_DIR = os.getcwd()
SERVICE_ACCOUNT_FILE = '/gcp_service_acc.json'

def gcp_api_client():
    credentials = service_account.Credentials.from_service_account_file(
            BASE_DIR + SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    return googleapiclient.discovery.build('healthcare', 'v1', credentials=credentials).projects().locations().services().nlp()

# nlpService = f'projects/{os.getenv("GCP_PROJECT_ID")}/locations/us-central1/services/nlp'
# body = \
# """
# {
# "documentContent": "percutaneous cardiovascular procedures without acute myocardial infarction, without coronary artery stent implant"
# }
# """
# nlp_client = api_client.analyzeEntities(nlpService=nlpService, body=json.loads(body))


# body = "{\"documentContent\":\"Insulin regimen human 5 units IV administered.\"}"
# api_client.body = json.dumps(body)
# api_client.method = "POST"
# api_client.body = body

# res = api_client.execute()
# print(res)