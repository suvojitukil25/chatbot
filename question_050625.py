import requests
from fastapi import FastAPI
import uvicorn
from sentence_transformers import SentenceTransformer, util
from datetime import datetime, timezone

####################### Token generation #########################
def access_token_generation():
    url = "https://api.ariba.com/v2/oauth/token"
    
    payload = 'grant_type=openapi_2lo'
    headers = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    'Authorization': 'Basic ODJmNjM1ODAtNTFjNy00Njk0LThjNjctYTA3YWUwNjY1ZTM4OllaMGxtcHk3eFdlQTd3czdHWXBkRDRjRnNreHNGZnFu',
    'Connection': 'keep-alive',
    'Content-Length': '22',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Host': 'api.ariba.com',
    'Postman-Token': '011b0664-f3e8-4a75-86ed-6bd06cede804,167d8722-bfb1-44b6-87c2-0e8b6096b7fe',
    'User-Agent': 'PostmanRuntime/7.19.0',
    'cache-control': 'no-cache,no-cache,no-cache'
    }
    
    response = requests.request("POST", url, headers=headers, data=payload)
    bearer_token = response.json()["access_token"] 
    return bearer_token

################## Json Extract ###############################
def json_extract(bearer_token): 
    url = f"https://openapi.ariba.com/api/retrieve-contract-workspaces/v1/prod/contractWorkspaces?user=BYOGARAJ&passwordAdapter=PasswordAdapter1&realm=744262602-T&$count=true"
    
    payload = {}
    headers = {
    'accept': 'application/json',
    'apiKey': 'BUwE6YUF0KhebIfmLxISduwAWqcnUJQP',
    'Authorization': f'Bearer {bearer_token}'
    }
    
    response = requests.request("GET", url, headers=headers, data=payload)
    
    data = response.json()
    return data


def semantic_search_question(query, question_set, thresold = 0.6):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    question_embeddings = model.encode(question_set,convert_to_tensor=True)
    query_embedding = model.encode(query,convert_to_tensor=True)
    scores = util.cos_sim(query_embedding,question_embeddings)[0]
    match_results = [(question_set[i], float(score)) for i, score in enumerate(scores) if score >= thresold]
    match_results.sort(key = lambda x: x[1], reverse = True)
    best_index = scores.argmax().item()
    best_match = (question_set[best_index], float(scores[best_index]))
    results = {"best_match":best_match, "matches_above_thresold":match_results}
    return results

##################### Answer based on question ###########################
def questionAnswer(question,data):
    if question == "how many contracts?":
        response = (f"{data['count']} contracts present")
    elif question == "how many contracts I have created?":
        owner = "AJAYASHE"   # Need to do dynamic
        count = 0
        for i in range(len(data['value'])):
            if owner.lower() == data['value'][i]['owner']['uniqueName'].lower():  # data['value'][i]['owner']['uniqueName'] returns owner name
                count += 1
        response = (f"{count} contracts you have created")
    elif question == "how many contracts are for process unity integration?":
        count = 0
        for i in range(len(data['value'])):
            for j in range(len(data['value'][i]['customFields'])):
                if "_ProcessUnityIntegrationRequired" in data['value'][i]['customFields'][j]['fieldId'] and data['value'][i]['customFields'][j]['booleanValue'] == True:
                    count +=1
        response = (f"{count} contracts are for process unity integration")
    elif question == "how many are expired?":
        count = 0
        for i in range(len(data['value'])):
            if data['value'][i]['contractStatus'] == "Expired":
                count += 1
        response = (f"{count} are expired")
    elif question == "how many are draft?":
        count = 0
        for i in range(len(data['value'])):
            if data['value'][i]['contractStatus'] == "Draft":
                count += 1
        response = (f"{count} are draft")
    elif question == "how many are completed?":
        count = 0
        for i in range(len(data['value'])):
            if data['value'][i]['contractStatus'] == "Completed":
                count += 1
        response = (f"{count} are completed")
    elif question == "how many contracts are created in US region":
        count = 0
        for i in range(len(data['value'])):
            for j in range(len(data['value'][i]['regions'])):
                if data['value'][i]['regions'][j]['uniqueName'] == "USA":
                    count += 1
        response = (f"{count} contracts are created in US region")
    elif question == "how many gonna expired within a month?":
        count = 0
        for i in range(len(data['value'])):
            expiration_str = data['value'][i]['expirationDate']
            expiration_date = datetime.strptime(expiration_str, "%Y-%m-%dT%H:%M:%S.%f%z")
            current_date = datetime.now(timezone.utc)
            if (expiration_date < current_date and expiration_date.year == current_date.year and expiration_date.month == current_date.month):
                count += 1
        response = (f"{count} will be expired within a month")
    elif question == "can you list down all the contracts , title, internal ID":
        contract_id_list = []
        title_list = []
        internal_id_list = []
        for i in range(len(data['value'])):
            for j in range(len(data['value'][i]['customFields'])):
                if "_ProcessUnityIntegrationRequired" in data['value'][i]['customFields'][j]['fieldId'] and data['value'][i]['customFields'][j]['booleanValue'] == True:
                    contract_id = data['value'][i]['contractId']
                    title = data['value'][i]['title']
                    internal_id = data['value'][i]['internalId']
                    contract_id_list.append(contract_id)
                    title_list.append(title)
                    internal_id_list.append(internal_id)
        response = {"<b>contract_id":contract_id_list,"<b>title":title_list,"<b>internal_id":internal_id_list}             
    else:
        response = ("No answer found")
    return response

app = FastAPI()

@app.get("/question")
async def question_answer(question: str):
    question_set = ["how many contracts?","how many contracts I have created?","how many contracts are for process unity integration?","how many are expired?","how many are draft?","how many are completed?","how many contracts are created in US region","how many gonna expired within a month?","can you list down all the contracts , title, internal ID"]
    question = question
    results = semantic_search_question(question,question_set, thresold = 0.6)
    if results['matches_above_thresold'] != []:
        bearer_token = access_token_generation()
        data = json_extract(bearer_token)       
        response = questionAnswer(results['best_match'][0], data)
        json_response = {"user_question": question, "mapping_question": results['best_match'][0], "answer":response, "matches_above_thresold": results['matches_above_thresold']}
    else:
        json_response = {"user_question": question, "mapping_question": "", "answer":"Please be more specific", "matches_above_thresold": results['matches_above_thresold']}
    return json_response

if __name__ == "__main__":
    uvicorn.run("question_050625:app",host="127.0.0.1", port = 8000)