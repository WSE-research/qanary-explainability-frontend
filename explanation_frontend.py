import streamlit as st
import requests
import logging
import json
from rdflib import Graph, Namespace

# Qanary components
NED_DBPEDIA = "NED-DBpediaSpotlight"
KG2KG = "KG2KG-TranslateAnnotationsOfInstanceToDBpediaOrWikidata"
NED_DANDELION = "DandelionNED"
QB_BIRTHDATA = "QB-BirthDataWikidata"
QB_SINA = "SINA"
QB_QANSWER = "QAnswerQueryBuilderAndQueryCandidateFetcher"
QB_PLATYPUS = "PlatypusQueryBuilder"
QE_SPARQLEXECUTER = "QE-SparqlQueryExecutedAutomaticallyOnWikidataOrDBpedia"
QBE_QANSWER = "QAnswerQueryBuilderAndExecutor"

CONFIG_ONE = ""
QANARY_PIPELINE_URL = "http://demos.swe.htwk-leipzig.de:40111"
QANARY_EXPLANATION_SERVICE_URL = "http://localhost:4000/explanations"


SPARQL_SELECT_EXPLANATION_QUERY = """
    PREFIX explanations: <urn:qanary:explanations#>
    CONSTRUCT {
        ?subject explanations:hasExplanationForCreatedData ?object .
    }
    WHERE {
        ?subject explanations:hasExplanationForCreatedData ?object .
        FILTER (LANG(?object) = "en")
    }
"""

explanationsNs = Namespace("urn:qanary:explanations#")

# The config is relevant for the pipeline execution, as it selects the used components
explanation_configurations_dict = {
    "Configuration 1": {
        "components": [NED_DBPEDIA, KG2KG, QB_BIRTHDATA, QE_SPARQLEXECUTER]
    },
    "Configuration 2": {

    },
    "Configuration 3": {

    },
    "Configuration 4": {

    },
    "Configuration 5": {

    }
}
explanation_configurations = explanation_configurations_dict.keys()

GPT3_5_TURBO = "GPT-3.5 (from OpenAI)"
GPT3_5_MODEL = "gpt-3.5-turbo"
GPT4 = "GPT-4 (from OpenAI)"
GPT4_MODEL = "gpt-4-XXX"
MODEL_KEY = "model"
SHOTS_KEY = "shots"
SEPARATOR = """, shots: """
ONESHOT = "1"  # "One-shot"
TWOSHOT = "2"
THREESHOT = "3"

# MODEL MAPPINGS
GPT3_5_ONE_SHOT = GPT3_5_TURBO + SEPARATOR + ONESHOT
GPT3_5_TWO_SHOT = GPT3_5_TURBO + SEPARATOR + TWOSHOT
GPT3_5_THREE_SHOT = GPT3_5_TURBO + SEPARATOR + THREESHOT
GPT4_ONE_SHOT = GPT4 + SEPARATOR + ONESHOT

# GPT models are relevant for the creation of the explanation
gptModels_dic = {
    GPT3_5_ONE_SHOT: {
        MODEL_KEY: GPT3_5_MODEL,
        SHOTS_KEY: 1
    },
    GPT3_5_TWO_SHOT: {
        MODEL_KEY: GPT3_5_MODEL,
        SHOTS_KEY: 2
    },
    GPT3_5_THREE_SHOT: {
        MODEL_KEY: GPT3_5_MODEL,
        SHOTS_KEY: 3
    },
    GPT4_ONE_SHOT: {
        MODEL_KEY: GPT4_MODEL,
        SHOTS_KEY: 1
    }
}

gptModels = gptModels_dic.keys()


########## Functions:
def execute_qanary_pipeline(question, components):
    component_list = ""
    for component in components['components']:
        component_list += "&componentlist[]=" + component
    print(component_list)

    custom_pipeline_url = f"{QANARY_PIPELINE_URL}/questionanswering?textquestion=" + question + component_list

    response = requests.post(custom_pipeline_url, {})
    logging.info("Qanary pipeline request response: " + str(response.status_code))

    return response


def request_explanations(question, components):
    # First: Execute Qanary pipeline
    qa_process_information = execute_qanary_pipeline(question, components)
    logging.info("QA-Process information: " + str(qa_process_information))
    graph = qa_process_information.json()["outGraph"]

    # Implement the explanation
    explanations = {}
    for component in components['components']:
        try:
            g = Graph()
            custom_explanation_url = f"{QANARY_EXPLANATION_SERVICE_URL}/{graph}/urn:qanary:{component}" # Prob. make explanations available through triplestore
            response = requests.get(custom_explanation_url, {})
            g.parse(data=response.text)
            component_rulebased_explanation = list(g[:explanationsNs.hasExplanationForCreatedData])
            component_generative_explanation = get_gpt_explanation()
            explanations[component] = {
                "rulebased": next(triple[1] for triple in component_rulebased_explanation if triple[1].language == 'en').value, # Probably establish a API to directly get the explanation, or, use a SELECT query here // move processing to backend
                "generative": component_generative_explanation
            }
        except Exception as error:
            print("An error occured while fetching the explanation for the component" + component + " with error: ", error)

    print(explanations)
    return explanations

def get_gpt_explanation():

    return ""


st.header('Qanary Explanation Demo')

with st.sidebar:
    st.subheader("Configurations")
    configuration = st.radio('Select a configuration, which youwant to test explanations for',
                             explanation_configurations, index=0)
    selected_configuration = explanation_configurations_dict[configuration]

    st.subheader('GPT Model')
    gptModel = st.radio('What GPT model should create the generative explanation?', gptModels, index=0)
    selected_gptModel = gptModels_dic[gptModel]

header_column, button_column = st.columns(2)

with header_column:
    st.subheader("Enter a question")

question, submit_question = st.columns([5, 1])

with question:
    text_question = st.text_input('Your question', 'Enter your question ...', label_visibility="hidden")
with submit_question:
    st.button('Send', on_click=request_explanations(text_question, selected_configuration))  # Pass components

# Implement details for Configuration and show the current selection's details
