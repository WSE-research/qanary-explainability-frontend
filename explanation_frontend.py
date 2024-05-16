import streamlit as st
import requests
import logging
import json
from rdflib import Namespace
import time

# Qanary components
NED_DBPEDIA = {
    "componentName": "NED-DBpediaSpotlight",
    "componentMainType": "AnnotationOfInstance"
}
KG2KG = {
    "componentName":"KG2KG-TranslateAnnotationsOfInstanceToDBpediaOrWikidata",
    "componentMainType":"AnnotationOfInstance"
}
NED_DANDELION = {
    "componentName":"DandelionNED",
    "componentMainType":"AnnotationOfInstance"
    }
QB_BIRTHDATA = {
    "componentName":"QB-BirthDataWikidata",
    "componentMainType":"AnnotationOfAnswerSPARQL"
}
QB_SINA = {
    "componentName":"SINA",
    "componentMainType":"AnnotationOfAnswerSPARQL"
    }
QB_QANSWER = {
    "componentName":"QAnswerQueryBuilderAndQueryCandidateFetcher",
    "componentMainType":"AnnotationOfAnswerSPARQL"
}
QB_PLATYPUS = {
    "componentName":"PlatypusQueryBuilder",
    "componentMainType":"AnnotationOfAnswerSPARQL"
}
QE_SPARQLEXECUTER = {
    "componentName":"QE-SparqlQueryExecutedAutomaticallyOnWikidataOrDBpedia",
    "componentMainType":"AnnotationOfAnswerJSON"
}
QBE_QANSWER = {
    "componentName":"QAnswerQueryBuilderAndExecutor",
    "componentMainType":"AnnotationOfAnswerJSON" # actually this component have several
}

CONFIG_ONE = "" # ?
QANARY_PIPELINE_URL = "http://localhost:8080"
QANARY_EXPLANATION_SERVICE_URL = "http://localhost:4000"


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
        "components": []
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
st.session_state.currentQaProcessExplanations = {}
st.session_state.componentsSelection = ()
st.session_state.pipelineFinished = False

###### FUNCTIONS 

def execute_qanary_pipeline(question, components):
    component_list = ""
    for component in components['components']:
        component_list += "&componentlist[]=" + component["componentName"]

    custom_pipeline_url = f"{QANARY_PIPELINE_URL}/questionanswering?textquestion=" + question + component_list
    response = requests.post(custom_pipeline_url, {})
    logging.info("Qanary pipeline request response: " + str(response.status_code))

    return response

def input_data_explanation(graph, json):
    input_explanation_url = f"{QANARY_EXPLANATION_SERVICE_URL}/composedexplanations/inputdata"
    response = requests.post(input_explanation_url, json, headers={"Accept":"application/json","Content-Type":"application/json"})
    return response.text

def convert_components_to_request_json_array(components):
    json = []
    for component in components:
        json.append(component)
    return json

def output_data_explanation(graph, json):
    output_explanation_url = f"{QANARY_EXPLANATION_SERVICE_URL}/composedexplanations/outputdata"
    return requests.post(output_explanation_url, json, headers={"Accept":"application/json","Content-Type":"application/json"}).text


def request_explanations(question, components):
    # First: Execute Qanary pipeline
    qa_process_information = execute_qanary_pipeline(question, components)
    logging.info("QA-Process information: " + str(qa_process_information))
    graph = qa_process_information.json()["outGraph"]

    json_data = json.dumps({
    "graphUri": graph,
    "generativeExplanationRequest": {
        "shots": gptModels_dic[gptModel][SHOTS_KEY],
        "gptModel": gptModels_dic[gptModel][MODEL_KEY],
        "qanaryComponents": components['components']
    }})

    #input_data_explanations = json.loads(input_data_explanation(graph,json_data))
    #output_data_explanations = output_data_explanations = output_data_explanation(graph,json_data)["explanationItems"]

    currentQaProcessExplanations = {}

    for component in components['components']:
        compName = component["componentName"]
        currentQaProcessExplanations[compName] = {
            "meta_information": {
                # add Meta information required for feedback
            },
            "input_data": {
                "rulebased": "PlaceholderRulebased", # input_data_explanations["explanationItems"][compName]["templatebased"],
                "generative": "PlaceholderGenerative" #input_data_explanations["explanationItems"][compName]["generative"]
            },
            "output_data": {
                "rulebased": "PlaceholderRulebased", #output_data_explanation["explanationItems"][compName]["templatebased"],
                "generative": "PlaceholderGenerative" #output_data_explanation["explanationItems"][compName]["generative"]
            }
        }

    st.session_state.currentQaProcessExplanations = currentQaProcessExplanations
    st.session_state.componentsSelection = currentQaProcessExplanations.keys()

def get_gpt_explanation():
    return ""

st.set_page_config(layout="wide")
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
    text_question = st.text_input('Your question', 'When was Albert Einstein born?', label_visibility="collapsed")
with submit_question:
    st.button('Send', on_click=request_explanations(text_question, selected_configuration))  # Pass components

st.divider()

# Show explanations and add selection

components = st.selectbox('Select component', st.session_state["componentsSelection"])

st.header("Template based explanations", divider="gray")
template_input, template_output = st.columns(2)
with template_input:
    st.subheader("Input")
    st.text_area("Template based explanation", st.session_state["currentQaProcessExplanations"][components]["input_data"]["rulebased"], label_visibility="collapsed")
with template_output:
    st.subheader("Output")
    st.text_area("Template based explanation2", st.session_state["currentQaProcessExplanations"][components]["output_data"]["rulebased"], label_visibility="collapsed")

# Add rating

st.header("Generative explanations", divider="gray")
generative_input, generative_output = st.columns(2)
with generative_input:
    st.subheader("Input")
    st.text_area("Generative generated explanation", st.session_state["currentQaProcessExplanations"][components]["input_data"]["generative"], label_visibility="collapsed")
with generative_output:
    st.subheader("Output")
    st.text_area("Generative generated explanation2", st.session_state["currentQaProcessExplanations"][components]["output_data"]["generative"], label_visibility="collapsed")

# Add rating -> Which information is required to store in triplestore?