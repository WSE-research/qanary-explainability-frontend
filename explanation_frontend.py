import streamlit as st
from streamlit.components.v1 import html
import requests
import logging
import json
from rdflib import Namespace
from util import include_css
from code_editor import code_editor

st.set_page_config(layout="wide")

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
    "componentMainType":"AnnotationOfAnswerJson"
}
QBE_QANSWER = {
    "componentName":"QAnswerQueryBuilderAndExecutor",
    "componentMainType":"AnnotationOfAnswerJson" # actually this component have several
}

CONFIG_ONE = "" # ?
QANARY_PIPELINE_URL = "http://localhost:8080"
QANARY_EXPLANATION_SERVICE_URL = "http://localhost:4000"
GITHUB_REPO = ""


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
        "components": [NED_DBPEDIA, KG2KG, QB_BIRTHDATA, QE_SPARQLEXECUTER],
        "exampleQuestions": "With this configuration, you can ask for a person's birthdate, e.g. When was Albert Einstein born?"
    },
    "Configuration 2": {
        "components": [],
        "exampleQuestions": "With this configuration, you can ask for a person's birthdate, e.g. When was Angela Merkel born?"
    },
    "Configuration 3": {

    },
    "Self configured": {
        "components": [],
        "exampleQuestions": ""
    }
}
explanation_configurations = explanation_configurations_dict.keys()

GPT3_5_TURBO = "GPT-3.5 (from OpenAI)"
GPT3_5_MODEL = "GPT_3_5"
GPT3_5_CONCRETE = "Concrete models: gpt-3.5-turbo-instruct / gpt-3.5-turbo-16k"
GPT4_CONCRETE = "Concrete model: gpt-4-0613"
CONCRETE_MODEL = "concrete_model"
GPT4 = "GPT-4 (from OpenAI)"
GPT4_MODEL = "GPT_4"
MODEL_KEY = "model"
SHOTS_KEY = "shots"
SEPARATOR = """, shots: """
ONESHOT = "1"  # "One-shot"
TWOSHOT = "2"
THREESHOT = "3"
GPT_MODEL_HELP = "The examples for the prompts are generated randomly by executing several QA processes with Qanary. The selection of the Annotation-Type and Component for these examples are automated to reduce complexity."

# MODEL MAPPINGS
GPT3_5_ONE_SHOT = GPT3_5_TURBO + SEPARATOR + ONESHOT
GPT3_5_TWO_SHOT = GPT3_5_TURBO + SEPARATOR + TWOSHOT
GPT3_5_THREE_SHOT = GPT3_5_TURBO + SEPARATOR + THREESHOT
GPT4_ONE_SHOT = GPT4 + SEPARATOR + ONESHOT

# GPT models are relevant for the creation of the explanation
gptModels_dic = {
    GPT3_5_ONE_SHOT: {
        MODEL_KEY: GPT3_5_MODEL,
        SHOTS_KEY: 1,
        CONCRETE_MODEL: GPT3_5_CONCRETE
    },
    GPT3_5_TWO_SHOT: {
        MODEL_KEY: GPT3_5_MODEL,
        SHOTS_KEY: 2,
        CONCRETE_MODEL: GPT3_5_CONCRETE
    },
    GPT3_5_THREE_SHOT: {
        MODEL_KEY: GPT3_5_MODEL,
        SHOTS_KEY: 3,
        CONCRETE_MODEL: GPT3_5_CONCRETE
    },
    GPT4_ONE_SHOT: {
        MODEL_KEY: GPT4_MODEL,
        SHOTS_KEY: 1,
        CONCRETE_MODEL: GPT4_CONCRETE
    }
}



gptModels = gptModels_dic.keys()
concrete_models = [value[CONCRETE_MODEL] for value in gptModels_dic.values()]
st.session_state.currentQaProcessExplanations = {}
st.session_state.componentsSelection = ()

###### FUNCTIONS 

@st.cache_data
def request_components_list():
    response = requests.get("http://demos.swe.htwk-leipzig.de:40111/components", {})
    data = json.loads(response.text)
    compList = []
    for object in data:
        compList.append(object["name"])
    return compList

st.session_state.componentsList = request_components_list()

@st.cache_data
def execute_qanary_pipeline(question, components):
    component_list = ""
    for component in components['components']:
        component_list += "&componentlist[]=" + component["componentName"]

    custom_pipeline_url = f"{QANARY_PIPELINE_URL}/questionanswering?textquestion=" + question + component_list
    response = requests.post(custom_pipeline_url, {})
    logging.info("Qanary pipeline request response: " + str(response.status_code))

    return response

@st.cache_data
def input_data_explanation(json):
    input_explanation_url = f"{QANARY_EXPLANATION_SERVICE_URL}/composedexplanations/inputdata"
    response = requests.post(input_explanation_url, json, headers={"Accept":"application/json","Content-Type":"application/json"})
    return response.text

def convert_components_to_request_json_array(components):
    json = []
    for component in components:
        json.append(component)
    return json

@st.cache_data
def output_data_explanation(json):
    output_explanation_url = f"{QANARY_EXPLANATION_SERVICE_URL}/composedexplanations/outputdata"
    return requests.post(output_explanation_url, json, headers={"Accept":"application/json","Content-Type":"application/json"}).text

def request_explanations(question, components, gptModel):
    qa_process_information = execute_qanary_pipeline(question, components).json()
    logging.info("QA-Process information: " + str(qa_process_information))
    graph = qa_process_information["outGraph"]

    json_data = json.dumps({
    "graphUri": graph,
    "generativeExplanationRequest": {
        "shots": gptModels_dic[gptModel][SHOTS_KEY],
        "gptModel": gptModels_dic[gptModel][MODEL_KEY],
        "qanaryComponents": components['components']
    }})

    input_data_explanations = json.loads(input_data_explanation(json_data))
    output_data_explanations = json.loads(output_data_explanation(json_data))

    currentQaProcessExplanations = {
        "components": {},
         "meta_information": {
            "graphUri": graph,
            "questionUri": qa_process_information["question"]
         }
    }

    for component in components['components']:
        compName = component["componentName"]
        currentQaProcessExplanations["components"][compName] = {
            "input_data": {
                "rulebased": input_data_explanations["explanationItems"][compName]["templatebased"],
                "generative": input_data_explanations["explanationItems"][compName]["generative"],
                "dataset": input_data_explanations["explanationItems"][compName]["dataset"]
            },
            "output_data": {
                "rulebased": output_data_explanations["explanationItems"][compName]["templatebased"],
                "generative": output_data_explanations["explanationItems"][compName]["generative"],
                "dataset" : output_data_explanations["explanationItems"][compName]["dataset"]
            }
        }

    st.session_state.currentQaProcessExplanations = currentQaProcessExplanations
    st.session_state.componentsSelection = currentQaProcessExplanations["components"].keys()

def get_gpt_explanation():
    return ""



include_css(st, ["css/style_github_ribbon.css"])
include_css(st, ["css/custom.css"])
st.header('Qanary Explanation Demo')

with st.sidebar:
    st.subheader("Configurations")
    configuration = st.radio('Select a configuration, which youwant to test explanations for',
                             explanation_configurations, index=0)
    selected_configuration = explanation_configurations_dict[configuration]

    if configuration == "Self configured":
        options = st.multiselect(
        "Chose your components",
        st.session_state.componentsList)
        selected_configuration["components"] = options

    st.subheader('GPT Model')
    gptModel = st.radio('What GPT model should create the generative explanation?', gptModels, index=0, help=GPT_MODEL_HELP, captions=concrete_models)
    selected_gptModel = gptModels_dic[gptModel]

header_column, button_column = st.columns(2)

with header_column:
    st.subheader("Enter a question")
    st.write(f'<span style="font-size: 1.1rem;">{selected_configuration["exampleQuestions"]}</span>', unsafe_allow_html=True)

question, submit_question = st.columns([5, 1])

with question:
    text_question = st.text_input('Your question', 'When was Albert Einstein born?', label_visibility="collapsed")
with submit_question:
    st.button('Send', on_click=request_explanations(text_question, selected_configuration, gptModel))  # Pass components

st.divider()

containerPipelineAndComponentsRadio = st.container(border=False)
questionID, graphUri, sparqlEndpoint = containerPipelineAndComponentsRadio.columns(3)
with questionID:
    st.write(f"**Question URI**: <span class='plainLink'>{st.session_state.currentQaProcessExplanations['meta_information']['questionUri']} </span>", unsafe_allow_html=True)
with graphUri:
    st.write(f"**Graph URI**: {st.session_state.currentQaProcessExplanations['meta_information']['graphUri']}")
with sparqlEndpoint:
    st.write(f"**SPARQL endpoint**: <span class='plainLink'>{QANARY_PIPELINE_URL}/sparql</span>", unsafe_allow_html=True)
#containerPipelineAndComponentsRadio.write(f"Qanary pipeline information:   Graph: {st.session_state.currentQaProcessExplanations['meta_information']['graphUri']} | Question ID:  | SPARQL endpoint: ")
selected_component = containerPipelineAndComponentsRadio.radio('', st.session_state["componentsSelection"], horizontal=True, index=0)

st.divider()

st.header("Input data explanations")
explanationInput, dataInput = st.columns(2)
with explanationInput:
    st.subheader("Template-based")
    st.write("", st.session_state["currentQaProcessExplanations"]["components"][selected_component]["input_data"]["rulebased"])
    st.subheader("Generative")
    st.write("", st.session_state["currentQaProcessExplanations"]["components"][selected_component]["input_data"]["generative"])
with dataInput:
    sparqlQuery = code_editor(st.session_state["currentQaProcessExplanations"]["components"][selected_component]["input_data"]["dataset"], lang="sparql", options={"wrap": False, "readOnly": True})

st.header("Output data explanations")
explanationOutput, dataOutput = st.columns(2)
with explanationOutput:
    st.subheader("Template-based")
    st.write("", st.session_state["currentQaProcessExplanations"]["components"][selected_component]["output_data"]["rulebased"])
    st.subheader("Generative")
    st.write("", st.session_state["currentQaProcessExplanations"]["components"][selected_component]["output_data"]["generative"])
with dataOutput:
    sparqlQuery = code_editor(st.session_state["currentQaProcessExplanations"]["components"][selected_component]["output_data"]["dataset"], lang="rdf/xml", options={"wrap": True, "readOnly": True})



# Additional HTML and JS

st.markdown("""
---
Brought to you by the [<img style="height:3ex;border:0" src="https://avatars.githubusercontent.com/u/120292474?s=96&v=4"> WSE research group](https://wse-research.org/?utm_source=loris&utm_medium=footer) at the [Leipzig University of Applied Sciences](https://www.htwk-leipzig.de/).

See our [GitHub team page](http://wse.technology/) for more projects and tools.
""", unsafe_allow_html=True)

with open("js/change_menu.js", "r") as f:
    javascript = f.read()
    html(f"<script style='display:none'>{javascript}</script>")

html("""
<script>
parent.window.document.querySelectorAll("section[data-testid='stFileUploadDropzone']").forEach(function(element) {
    element.classList.add("fileDropHover")   
});

github_ribbon = parent.window.document.createElement("div");            
github_ribbon.innerHTML = '<a id="github-fork-ribbon" class="github-fork-ribbon right-bottom" href="%s" target="_blank" data-ribbon="Fork me on GitHub" title="Fork me on GitHub">Fork me on GitHub</a>';
if (parent.window.document.getElementById("github-fork-ribbon") == null) {
    parent.window.document.body.appendChild(github_ribbon.firstChild);
}
</script>
""" % (GITHUB_REPO,))