import logging
import streamlit as st
from streamlit.components.v1 import html
import requests
import json
from util import include_css, get_random_element, feedback_messages, feedback_icons
from code_editor import code_editor
import pandas as pd
from decouple import config
import pymongo

st.set_page_config(layout="wide")
include_css(st, ["css/style_github_ribbon.css"])
include_css(st, ["css/custom.css"])

### Qanary components for pre-defined configurations
NED_DBPEDIA = "NED-DBpediaSpotlight"
KG2KG = "KG2KG-TranslateAnnotationsOfInstanceToDBpediaOrWikidata"
QB_BIRTHDATA = "QB-BirthDataWikidata"
QB_SINA = "SINA"
QB_QANSWER = "QAnswerQueryBuilderAndQueryCandidateFetcher"
QB_PLATYPUS = "PlatypusQueryBuilder"
QE_SPARQLEXECUTER = "QE-SparqlQueryExecutedAutomaticallyOnWikidataOrDBpedia"
QBE_QANSWER = "QAnswerQueryBuilderAndExecutor"
FEEDBACK_BAD = 0
FEEDBACK_GOOD = 1

QANARY_PIPELINE_URL = config('QANARY_PIPELINE_URL')
QANARY_EXPLANATION_SERVICE_URL = config('QANARY_EXPLANATION_SERVICE_URL')
QANARY_PIPELINE_COMPONENTS = config('QANARY_PIPELINE_COMPONENTS')
GITHUB_REPO = config('GITHUB_REPO')
FEEDBACK_URL = config('FEEDBACK_URL')

### Pre-defined configurations
explanation_configurations_dict = {
    "Configuration 1": {
        "components": [NED_DBPEDIA, KG2KG, QB_BIRTHDATA, QE_SPARQLEXECUTER],
        "exampleQuestions": [
            "What is the birth date of Albert Einstein?",
            "When was Albert Einstein born?",
            "What is the birth date of Jesus Christ?",
        ]
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

### Constants
GPT3_5_TURBO = "GPT-3.5 (from OpenAI)"
GPT3_5_MODEL = "GPT_3_5"
GPT3_5_CONCRETE = "Concrete models: gpt-3.5-turbo-instruct / gpt-3.5-turbo-16k"
GPT4_CONCRETE = "Concrete model: gpt-4-0613"
CONCRETE_MODEL = "concrete_model"
GPT4 = "GPT-4 (from OpenAI)"
GPT4_MODEL = "GPT_4"
MODEL_KEY = "model"
SHOTS_KEY = "shots"
SHOT = "-shot"
ZEROSHOT = "0"
ONESHOT = "1"  # "One-shot"
TWOSHOT = "2"
THREESHOT = "3"
GPT_MODEL_HELP = "The examples for the prompts are generated randomly by executing several QA processes with Qanary. The selection of the Annotation-Type and Component for these examples are automated to reduce complexity."

### MODEL MAPPINGS
GPT_3_5_ZERO_SHOT = GPT3_5_TURBO + ", " + ZEROSHOT + SHOT
GPT3_5_ONE_SHOT = GPT3_5_TURBO + ", " + ONESHOT + SHOT
GPT3_5_TWO_SHOT = GPT3_5_TURBO + ", " + TWOSHOT + SHOT
GPT3_5_THREE_SHOT = GPT3_5_TURBO + "," + THREESHOT + SHOT
GPT4_ZERO_SHOT = GPT4 + ", " + ZEROSHOT + SHOT
GPT4_ONE_SHOT = GPT4 + ", " + ONESHOT + SHOT + ":star:"

### Selectable GPT models
gptModels_dic = {
    GPT_3_5_ZERO_SHOT: {
        MODEL_KEY: GPT3_5_MODEL,
        SHOTS_KEY: 0,
        CONCRETE_MODEL: GPT3_5_CONCRETE
    },    
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
    GPT4_ZERO_SHOT: {
        MODEL_KEY: GPT4_MODEL,
        SHOTS_KEY: 0,
        CONCRETE_MODEL: GPT4_CONCRETE
    },
    GPT4_ONE_SHOT: {
        MODEL_KEY: GPT4_MODEL,
        SHOTS_KEY: 1,
        CONCRETE_MODEL: GPT4_CONCRETE
    }

}
gptModels = gptModels_dic.keys()
concrete_models = [value[CONCRETE_MODEL] for value in gptModels_dic.values()]

### Initialize sessions states
if'pipeline_finished' not in st.session_state:
    st.session_state.pipeline_finished = False
if 'qanary_components' not in st.session_state:
    st.session_state.qanary_components = []
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
if "showPreconfigured" not in st.session_state:
    st.session_state.showPreconfigured = True;

mongo_client = pymongo.MongoClient(config('FEEDBACK_URL'),
    username=config('MONGO_USER'),
    password=config('MONGO_PASSWORD'),
    authSource=config('MONGO_AUTHSOURCE'),
)
explanationsDb = mongo_client["explanations"]
explanationsCol = explanationsDb["explanation"]

###### FUNCTIONS 

# Fetches the available components from the associated Qanary pipeline
@st.cache_data
def request_components_list():
    try:
        response = requests.get(QANARY_PIPELINE_COMPONENTS, headers={"Accept":"application/json"}) # Auslagern der URL
        data = json.loads(response.text)
        components = []
        for key in data:
            components.append(key["name"])
        return components
    except Exception as e:
        raise Exception("Error while fetching the components: " + str(e))

# Executes the Qanary pipeline with the passed components, the gptModel attr is passed to check whether it must be executed or can be taken from the cache
@st.cache_data
def execute_qanary_pipeline(question, components, gptModel):
    component_list = ""
    for component in components:
        component_list += "&componentlist[]=" + component
    custom_pipeline_url = f"{QANARY_PIPELINE_URL}/questionanswering?textquestion=" + question + component_list
    try:
        response = requests.post(custom_pipeline_url, {})
        return response
    except Exception as e:
        return e

# Fetches the explanations for the input data
@st.cache_data
def input_data_explanation(json):
    input_explanation_url = f"{QANARY_EXPLANATION_SERVICE_URL}/composedexplanations/inputdata"
    response = requests.post(input_explanation_url, json, headers={"Accept":"application/json","Content-Type":"application/json"})
    if(200 <= response.status_code < 300):
        return response.text
    else:
        raise Exception("Error while fetching the input data explanations: " + response.text)

# Fetches the explanations for the output data
@st.cache_data
def output_data_explanation(json):
    output_explanation_url = f"{QANARY_EXPLANATION_SERVICE_URL}/composedexplanations/outputdata"
    response = requests.post(output_explanation_url, json, headers={"Accept":"application/json","Content-Type":"application/json"})
    if(response.status_code != 200):
        raise Exception("Error while fetching the output data explanations: " + response.text)
    elif(200 <= response.status_code < 300):
        return response.text

# Helper function to convert the dict to a array of components # TODO: Needed!?
def convert_component_dir_to_list(componentDir):
    component_list = []
    for component in componentDir:
        component_list.append(component)
    return component_list

# Switches view when configuration switch is invoked, therefore, some session states have to be set to the default value
def switch_view():
    st.session_state.explanations_generated = False
    st.session_state.pipeline_finished = False
    st.session_state.selected_component = ""
    st.session_state.showPreconfigured = not st.session_state.showPreconfigured
    st.session_state.process_active = False

# Outsourced method to create a new dict
def createExplanationDict(input, output):
    return {
                "input_data": {
                "rulebased": input["templatebased"],
                "generative": input["generative"].lstrip("\n"),
                "dataset": input["dataset"],
                "prompt": input["prompt"]
            },
            "output_data": {
                "rulebased": output["templatebased"],
                "generative": output["generative"].lstrip("\n"),
                "dataset" : output["dataset"],
                "prompt": output["prompt"]
            }
    }

# wrapper function, handles the request for explanations
def request_explanations(question, gptModel):
    st.session_state.explanations_generated = False
    st.session_state.process_active = True
    components = convert_component_dir_to_list(st.session_state.selected_configuration["components"])
    try:
        qa_process_information = execute_qanary_pipeline(question, components, gptModel).json()
        st.session_state.pipeline_finished = True
        graph = qa_process_information["outGraph"]
        json_data = json.dumps({
        "graphUri": graph,
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
            input = input_data_explanations["explanationItems"][component]
            output = output_data_explanations["explanationItems"][component]
            currentQaProcessExplanations["components"][component] = createExplanationDict(input, output)

        st.session_state.currentQaProcessExplanations = currentQaProcessExplanations
        st.session_state.componentsSelection = currentQaProcessExplanations["components"].keys()
        st.session_state.explanations_generated = True
    except Exception as e:
        logging.error("Error while executing the Qanary pipeline: " + str(e))
        st.error("Error while executing the Qanary pipeline. Try another configuration or try again later.")
        st.session_state.pipeline_finished = False
        st.cache_data.clear()

##### definitions for configurations

def showExplanationContainer(component, lang, plainKey, datasetTitle):
    generative = (component["generative"]).strip("\n")
    template = (component["rulebased"]).strip("\n")
    with st.container(border=False):
        with st.expander(datasetTitle):
            code_editor(component["dataset"],lang=lang, theme="default", options={"wrap": True})
        with st.expander("Prompt"):
            code_editor(component["prompt"], lang="turtle", theme="default", options={"wrap": True})
        templateCol, generativeCol = st.columns([0.5,0.5])
        with templateCol:
            st.markdown(f"""<h3>Template</h3>""", unsafe_allow_html=True)
            st.markdown(f"""<div style="margin-bottom: 25px;">{template}</div>""", unsafe_allow_html=True)
            placeholder1, col1, col2, placeholder2 = st.columns(4)
            with col1:
                feedback_button(plainKey+"template"+"correct",":white_check_mark:", "template", template, plainKey, FEEDBACK_GOOD)
            with col2:
                feedback_button(plainKey+"template"+"wrong",":x:", "template", template, plainKey, FEEDBACK_BAD)
        with generativeCol:
            st.markdown(f"""<h3>Generative</h3>""", unsafe_allow_html=True)
            st.markdown(f"""<div style="margin-bottom: 25px;">{generative}</div>""", unsafe_allow_html=True)
            placeholder1, col1, col2, placeholder2 = st.columns(4)
            with col1:
                feedback_button(plainKey+"generative"+"correct",":white_check_mark:", "generative", generative, plainKey, FEEDBACK_GOOD)
            with col2:
                feedback_button(plainKey+"generative"+"wrong",":x:", "generative", generative, plainKey, FEEDBACK_BAD)

def feedback_button(key, icon, type, explanation, datatype, feedback):
    if st.button(icon, key=key, type="secondary"):
        send_feedback(explanation=explanation, explanation_type=type, datatype=datatype, feedback=feedback)
        st.toast(get_random_element(feedback_messages), icon=get_random_element(feedback_icons))

def send_feedback(explanation, explanation_type, datatype, feedback):
    json= {
            "graph": st.session_state.currentQaProcessExplanations["meta_information"]["graphUri"],
            "component": st.session_state.selected_component,
            "explanation": explanation,
            "explanation_type": explanation_type,
            "datatype": datatype,
            "gpt_model": st.session_state.selected_gptModel["concrete_model"],
            "shots": st.session_state.selected_gptModel["shots"],
            "feedback": feedback
        }
    try: 
        response = explanationsCol.insert_one(json)
    except Exception as e:
        logging.error("Feedback wasn't sent: " + str(e))
        st.error("Feedback wasn't sent. Sorry for the circumstances.")

def show_meta_data():
    if st.session_state.pipeline_finished:
        containerPipelineAndComponentsRadio = st.container(border=False)
        questionID, graphUri, sparqlEndpoint = containerPipelineAndComponentsRadio.columns(3)
        with questionID:
            st.write(f"**Question URI**: <span class='plainLink'>{st.session_state.currentQaProcessExplanations['meta_information']['questionUri']} </span>", unsafe_allow_html=True)
        with graphUri:
            st.markdown(f"<p><b>Graph:</b> {st.session_state.currentQaProcessExplanations['meta_information']['graphUri']}</p>", unsafe_allow_html=True)
        with sparqlEndpoint:
            st.write(f"**SPARQL endpoint**: <span class='plainLink'>{QANARY_PIPELINE_URL}/sparql</span>", unsafe_allow_html=True)
        st.session_state.selected_component = containerPipelineAndComponentsRadio.radio('', st.session_state["componentsSelection"], horizontal=True, index=0)

def show_explanations():
        if st.session_state.selected_configuration["components"]:
            st.header("Input data explanations")
            showExplanationContainer(st.session_state["currentQaProcessExplanations"]["components"][st.session_state.selected_component]["input_data"], "sparql", "input","SPARQL query")
            st.markdown("""<div class="custom-divider"></div>""",unsafe_allow_html=True)
            st.header("Output data explanations")
            showExplanationContainer(st.session_state["currentQaProcessExplanations"]["components"][st.session_state.selected_component]["output_data"], "turtle", "output", "RDF Triples")
        else:
            st.write("You haven't selected a configuration or individual components")

def exampleQuestion(key, question): 
    button, text = st.columns([0.04,0.96])
    with button:
        if st.button(key=key,label=":heavy_plus_sign:"):
            st.session_state.text_question = question
    with text:
        st.write(question)

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

    st.session_state.selected_configuration["components"] = st.multiselect(label="Select your components in the correct order", label_visibility="hidden",options=componentsNames, key="compSelectionIndividual", placeholder="Choose your desired components")

    pre_configured()

### START STREAMLIT APP

st.header('Qanary Explanation Demo')

with st.sidebar:
    if st.session_state.showPreconfigured:
        st.subheader("Default configurations", help="Select a pre-defined configuration to start the Qanary pipeline with.")
        configuration = st.radio(label='Select a configuration:',options=explanation_configurations, index=0, label_visibility="collapsed")
        st.session_state.selected_configuration = explanation_configurations_dict[configuration] # Make it a session state
        configButton = st.button("Change configuration", on_click=lambda: switch_view())
    st.subheader('GPT Model', help="Select a GPT model to generate the generative explanation. Please note that an explanation with more shots will take longer to generate.")
    gptModel = st.radio('What GPT model should create the generative explanation?', label_visibility="collapsed", options=gptModels, index=0, help=GPT_MODEL_HELP, captions=concrete_models)
    selected_gptModel = gptModels_dic[gptModel]
    if not st.session_state.showPreconfigured:
        configButton = st.button("Change configuration", on_click=lambda: switch_view())

header_column, button_column = st.columns(2)

with header_column:
    st.subheader("Enter a question")

question, submit_question = st.columns([5, 1])

with question:
    placeholder = st.empty()
with submit_question:
    st.button('Send', on_click=lambda: request_explanations(text_question, gptModel))

if st.session_state.showPreconfigured:    
    with st.expander("Example questions"):
        for question in st.session_state.selected_configuration["exampleQuestions"]:
            exampleQuestion(question, question)

text_question = placeholder.text_input(key="text_question", label='Your question', value="When was Albert Einstein born?", label_visibility="collapsed")

# Select whether showPreconfigured is True or False

if st.session_state.showPreconfigured:
    pre_configured()
elif not st.session_state.showPreconfigured:
    not_pre_configured()

### Additional HTML and JS

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