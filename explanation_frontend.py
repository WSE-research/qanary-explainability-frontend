import streamlit as st
from streamlit.components.v1 import html
import requests
import json
from rdflib import Namespace
from util import include_css
from code_editor import code_editor
from st_aggrid import GridOptionsBuilder, AgGrid
import pandas as pd
from streamlit_sortables import sort_items
from decouple import config

st.set_page_config(layout="wide")

# Qanary components
NED_DBPEDIA = "NED-DBpediaSpotlight"
KG2KG = "KG2KG-TranslateAnnotationsOfInstanceToDBpediaOrWikidata"
QB_BIRTHDATA = "QB-BirthDataWikidata"
QB_SINA = "SINA"
QB_QANSWER = "QAnswerQueryBuilderAndQueryCandidateFetcher"
QB_PLATYPUS = "PlatypusQueryBuilder"
QE_SPARQLEXECUTER = "QE-SparqlQueryExecutedAutomaticallyOnWikidataOrDBpedia"
QBE_QANSWER = "QAnswerQueryBuilderAndExecutor"

QANARY_PIPELINE_URL = config('QANARY_PIPELINE_URL')
QANARY_EXPLANATION_SERVICE_URL = config('QANARY_EXPLANATION_SERVICE_URL')
QANARY_PIPELINE_COMPONENTS = config('QANARY_PIPELINE_COMPONENTS')
GITHUB_REPO = config('GITHUB_REPO')


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
        "components": [NED_DBPEDIA, KG2KG, QB_BIRTHDATA, QE_SPARQLEXECUTER],
        "exampleQuestions": ""
    },
    "Configuration 3": {
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

if'pipeline_finished' not in st.session_state:
    st.session_state['pipeline_finished'] = False
if 'qanary_components' not in st.session_state:
    st.session_state['qanary_components'] = []
if 'explanations_generated' not in st.session_state:
    st.session_state.explanations_generated = False
if 'selected_component' not in st.session_state:
    st.session_state.selected_component = ""
if 'process_active' not in st.session_state:
    st.session_state.process_active = False
if 'currentQaProcessExplanations' not in st.session_state:
    st.session_state.currentQaProcessExplanations = {}
if 'selected_configuration' not in st.session_state:
    st.session_state.selected_configuration = {}

###### FUNCTIONS 

@st.cache_data
def request_components_list():
    response = requests.get(QANARY_PIPELINE_COMPONENTS, headers={"Accept":"application/json"}) # Auslagern der URL
    data = json.loads(response.text)
    components = []
    for key in data:
        components.append(key["name"])
    return components

@st.cache_data
def execute_qanary_pipeline(question, components):
    component_list = ""
    for component in components:
        component_list += "&componentlist[]=" + component

    custom_pipeline_url = f"{QANARY_PIPELINE_URL}/questionanswering?textquestion=" + question + component_list
    print("Executing post request on: " + custom_pipeline_url)
    return requests.post(custom_pipeline_url, {})

@st.cache_data
def input_data_explanation(json):
    input_explanation_url = f"{QANARY_EXPLANATION_SERVICE_URL}/composedexplanations/inputdata/example"
    response = requests.post(input_explanation_url, json, headers={"Accept":"application/json","Content-Type":"application/json"})
    return response.text

@st.cache_data
def output_data_explanation(json):
    output_explanation_url = f"{QANARY_EXPLANATION_SERVICE_URL}/composedexplanations/outputdata/example"
    return requests.post(output_explanation_url, json, headers={"Accept":"application/json","Content-Type":"application/json"}).text

def convert_component_dir_to_list(componentDir):
    component_list = []
    for component in componentDir:
        component_list.append(component)
    return component_list

def switch_view():
    st.session_state.explanations_generated = False
    st.session_state.pipeline_finished = False
    st.session_state.selected_component = ""
    st.session_state.showPreconfigured = not st.session_state.showPreconfigured
    st.session_state.process_active = False


def request_explanations(question, gptModel):
    st.session_state.explanations_generated = False
    st.session_state.process_active = True
    components = convert_component_dir_to_list(st.session_state.selected_configuration["components"])
    print("DIct: " + str(components))
    qa_process_information = execute_qanary_pipeline(question, components).json()
    #qa_process_information = json.loads(execute_qanary_pipeline(question, components))
    st.session_state.pipeline_finished = True
    graph = qa_process_information["outGraph"]

    json_data = json.dumps({
    "graphUri": "graph",
    "generativeExplanationRequest": {
        "shots": gptModels_dic[gptModel][SHOTS_KEY], #Rename gpt models dict as it contains the shots value
        "gptModel": gptModels_dic[gptModel][MODEL_KEY],
        "qanaryComponents": components
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

    for component in components:
        currentQaProcessExplanations["components"][component] = {
            "input_data": {
                "rulebased": input_data_explanations["explanationItems"][component]["templatebased"],
                "generative": input_data_explanations["explanationItems"][component]["generative"],
                "dataset": input_data_explanations["explanationItems"][component]["dataset"]
            },
            "output_data": {
                "rulebased": output_data_explanations["explanationItems"][component]["templatebased"],
                "generative": output_data_explanations["explanationItems"][component]["generative"],
                "dataset" : output_data_explanations["explanationItems"][component]["dataset"]
            }
        }

    st.session_state.currentQaProcessExplanations = currentQaProcessExplanations
    st.session_state.componentsSelection = currentQaProcessExplanations["components"].keys()
    st.session_state.explanations_generated = True

if "showPreconfigured" not in st.session_state:
    st.session_state.showPreconfigured = True;

include_css(st, ["css/style_github_ribbon.css"])
include_css(st, ["css/custom.css"])
st.header('Qanary Explanation Demo')


with st.sidebar:
    if st.session_state.showPreconfigured:
        st.subheader("Configurations")
        configuration = st.radio('Select a configuration, which youwant to test explanations for',
                                explanation_configurations, index=0)
        st.session_state.selected_configuration = explanation_configurations_dict[configuration] # Make it a session state

    st.subheader('GPT Model')
    gptModel = st.radio('What GPT model should create the generative explanation?', gptModels, index=0, help=GPT_MODEL_HELP, captions=concrete_models)
    selected_gptModel = gptModels_dic[gptModel]

    configButton = st.button("Change configuration", on_click=lambda: switch_view())

##### Header config

header_column, button_column = st.columns(2)

with header_column:
    st.subheader("Enter a question")
#    st.write(f'<span style="font-size: 1.1rem;">{st.session_state.selected_configuration["exampleQuestions"]}</span>', unsafe_allow_html=True)

question, submit_question = st.columns([5, 1])

with question:
    text_question = st.text_input('Your question', 'When was Albert Einstein born?', label_visibility="collapsed")
with submit_question:
    st.button('Send', on_click=lambda: request_explanations(text_question, gptModel))



##### definitions for configurations

def show_meta_data():
    if st.session_state.pipeline_finished:
        containerPipelineAndComponentsRadio = st.container(border=False)
        questionID, graphUri, sparqlEndpoint = containerPipelineAndComponentsRadio.columns(3)
        with questionID:
            st.write(f"**Question URI**: <span class='plainLink'>{st.session_state.currentQaProcessExplanations['meta_information']['questionUri']} </span>", unsafe_allow_html=True)
        with graphUri:
            st.write(f"**Graph URI**: {st.session_state.currentQaProcessExplanations['meta_information']['graphUri']}")
        with sparqlEndpoint:
            st.write(f"**SPARQL endpoint**: <span class='plainLink'>{QANARY_PIPELINE_URL}/sparql</span>", unsafe_allow_html=True)
        st.session_state.selected_component = containerPipelineAndComponentsRadio.radio('', st.session_state["componentsSelection"], horizontal=True, index=0)

def show_explanations():
        if st.session_state.selected_configuration["components"]:
            st.header("Input data explanations")
            explanationInput, dataInput = st.columns(2)
            with explanationInput:
                st.subheader("Template-based")
                st.write("", st.session_state["currentQaProcessExplanations"]["components"][st.session_state.selected_component]["input_data"]["rulebased"])
                st.subheader("Generative")
                st.write("", st.session_state["currentQaProcessExplanations"]["components"][st.session_state.selected_component]["input_data"]["generative"])
            with dataInput:
                sparqlQuery = code_editor(st.session_state["currentQaProcessExplanations"]["components"][st.session_state.selected_component]["input_data"]["dataset"], lang="sparql", options={"wrap": False, "readOnly": True})

            st.header("Output data explanations")
            explanationOutput, dataOutput = st.columns(2)
            with explanationOutput:
                st.subheader("Template-based")
                st.write("", st.session_state["currentQaProcessExplanations"]["components"][st.session_state.selected_component]["output_data"]["rulebased"])
                st.subheader("Generative")
                st.write("", st.session_state["currentQaProcessExplanations"]["components"][st.session_state.selected_component]["output_data"]["generative"])
            with dataOutput:
                rdfData = code_editor(st.session_state["currentQaProcessExplanations"]["components"][st.session_state.selected_component]["output_data"]["dataset"], lang="rdf/xml", options={"wrap": True, "readOnly": True})

        else:
            st.write("You haven't selected a configuration or individual components")

##### Configured
def pre_configured():
    if st.session_state.pipeline_finished:
        show_meta_data()
        st.divider()
    if st.session_state.explanations_generated:
        show_explanations()

##### Not configured

def not_pre_configured():
    components = request_components_list()
    componentsNames = convert_component_dir_to_list(components)
    st.session_state.selected_configuration = {"components":{}}

    st.subheader("Select components for the Qanary pipeline execution")

    # Grid and store order and selected components in session store 
    # grid = componentsGrid(components=components)

    st.session_state.selected_configuration["components"] = st.multiselect(label="Select your components in the correct order", label_visibility="hidden",options=componentsNames, key="compSelectionIndividual", placeholder="Choose your desired components")

    if st.session_state.pipeline_finished:
        st.divider()
        show_meta_data()
        st.divider()
    if st.session_state.explanations_generated:
        show_explanations()


def componentsGrid(components):
    df = pd.read_json(json.dumps(components))
    gb = GridOptionsBuilder.from_dataframe(df)
    gridOptions = gb.build()

    return AgGrid(df, gridOptions=gridOptions)

#####


# Select whether showPreconfigured is True or False

if st.session_state.showPreconfigured:
    pre_configured()
elif not st.session_state.showPreconfigured:
    not_pre_configured()


    
























###### Additional HTML and JS

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