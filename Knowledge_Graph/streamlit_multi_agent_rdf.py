import os
import asyncio
import tempfile
import json

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
load_dotenv()
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from autogen_core import CancellationToken
from rdflib import Graph, Literal, URIRef, Namespace
from rdflib.namespace import RDF, RDFS, XSD
from autogen_core import CancellationToken
import streamlit as st
import rdflib
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.messages import TextMessage


# visualization
import networkx as nx
from pyvis.network import Network
from langchain_core.documents import Document

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY not set in environment. Set it in .env and reload.")
    st.stop()

def get_model_client(model: str = "gpt-4o"):
    """
    Initialize and return a ChatOpenAI model client with the specified model.
    
    Args:
        model (str): The OpenAI model to use (default: "gpt-4o")
        
    Returns:
        ChatOpenAI: Initialized model client
    """
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in environment variables.")
    
    # Initialize the llm for the graph builder
    model_client = ChatOpenAI(model=model, temperature=0, api_key=OPENAI_API_KEY)
    return model_client


# Helper function to clean URI labels
def clean_uri(uri_str):
    # Remove namespace prefix (everything before #, / or last :)
    for sep in ['#', '/', ':']:
        if sep in uri_str:
            return uri_str.split(sep)[-1]
    return uri_str
    
def build_from_text(text: str, model: str = "gpt-4o"):
    """
    Given unstructured text, use LLMGraphTransformer to produce graph_documents
    and build an rdflib.Graph.
    
    Args:
        text (str): Unstructured text to convert to RDF
        model (str): OpenAI model to use (default: "gpt-4o")
        
    Returns:
        tuple: (graph_documents, rdflib.Graph)
    """
    if not text or not text.strip():
        raise ValueError("Input text is empty.")

    # Get model client and create transformer
    model_client = get_model_client(model=model)
    llm_transformer = LLMGraphTransformer(llm=model_client)

    # Convert text to graph documents
    docs = [Document(page_content=text)]
    graph_documents = llm_transformer.convert_to_graph_documents(docs)
    
    # Build RDF graph from documents
    rdf_graph = Graph()
    
    # Define namespaces
    EX = Namespace("http://example.org/ontology/")
    rdf_graph.bind("ex", EX)
    rdf_graph.bind("rdf", RDF)
    rdf_graph.bind("rdfs", RDFS)
    rdf_graph.bind("xsd", XSD)

    # Add nodes to graph
    for gd in graph_documents:
        for node in gd.nodes:
            subject = URIRef(EX[node.id.replace(" ", "_")])
            rdf_graph.add((subject, RDF.type, EX[node.type]))
            rdf_graph.add((subject, RDFS.label, Literal(node.id)))

            # Add node properties
            for key, value in node.properties.items():
                predicate = URIRef(EX[key.replace(" ", "_")])
                rdf_graph.add((subject, predicate, Literal(value)))

        # Add relationships to graph
        for rel in gd.relationships:
            subject = URIRef(EX[rel.source.id.replace(" ", "_")])
            predicate = URIRef(EX[rel.type.replace(" ", "_")])
            obj = URIRef(EX[rel.target.id.replace(" ", "_")])
            rdf_graph.add((subject, predicate, obj))

            # Add relationship properties
            for key, value in rel.properties.items():
                rel_prop_predicate = URIRef(EX[f"{rel.type.replace(' ', '_')}_{key.replace(' ', '_')}"])
                rdf_graph.add((subject, rel_prop_predicate, Literal(value)))

    return graph_documents, rdf_graph

st.set_page_config(page_title="Multi-Agent RDF Builder", layout="wide")
st.title("Multi-Agent RDF Knowledge Graph Builder")

st.markdown(
    "Enter unstructured text and press Build. A Planner agent will clean the text; "
    "the Graph agent will then invoke the registered RDF builder tool. The agent will call the tool "
    "by returning a small JSON payload which the app will execute."
)

pipeline = st.radio("Agent pipeline (demo):", ("Planner -> GraphAgent", "Direct GraphAgent"))

user_text = st.text_area("Paste unstructured text here:", height=200)

# Simple local tool registry: register python functions the agents can "call".
TOOL_REGISTRY = {
    "build_from_text": build_from_text
}

if st.button("Build RDF Knowledge Graph"):

    if not user_text.strip():
        st.warning("Please provide some unstructured text.")
        st.stop()

    st.info("Launching agents... this may take a few seconds.")

    model_client = OpenAIChatCompletionClient(model="gpt-4o", api_key=OPENAI_API_KEY)

    planner_agent = AssistantAgent(
        name="PlannerAgent",
        model_client=model_client,
        description="A planning agent that reformats and clarifies the user's unstructured text for graph extraction.",
        system_message=(
            "You are a Planner. Given unstructured text, produce a short cleaned text that "
            "focuses on entities, relations and facts. Return the cleaned text only."
        ),
    )

    # GraphAgent is instructed to CALL a tool by outputting a JSON payload:
    # {"tool":"build_from_text", "args": {"text": "...", "model":"gpt-4o"}}
    # The app will parse this JSON and execute the corresponding registered function.
    graph_agent = AssistantAgent(
        name="GraphAgent",
        model_client=model_client,
        description="A graph agent that receives cleaned text and should call the local RDF tool.",
        system_message=(
            "You are a GraphAgent. Receive the cleaned text and produce a JSON payload (no additional text) "
            "with this exact structure to invoke the RDF builder tool:\n"
            '{"tool":"build_from_text","args":{"text":"<CLEANED_TEXT>","model":"gpt-4o"}}\n'
            "Do not add commentary. Replace <CLEANED_TEXT> with the cleaned text to extract."
        ),
    )

    async def run_pipeline(text: str):
        cancellation_token = CancellationToken()
        # Planner step
        planner_resp = await planner_agent.on_messages(
            messages=[TextMessage(content=text, source="User")],
            cancellation_token=cancellation_token  # Add cancellation token
        )
        planner_output = ""
        if hasattr(planner_resp, "inner_messages"):
            for m in planner_resp.inner_messages:
                if getattr(m, "content", None):
                    planner_output += m.content + "\n"
        planner_output = planner_output.strip() or text

        if pipeline.startswith("Planner"):
            graph_input = planner_output
            graph_resp = await graph_agent.on_messages(
                messages=[TextMessage(content=graph_input, source="Planner")],
                cancellation_token = cancellation_token 
            )
            graph_output = ""
            if hasattr(graph_resp, "inner_messages"):
                for m in graph_resp.inner_messages:
                    if getattr(m, "content", None):
                        graph_output += m.content + "\n"
            graph_output = graph_output.strip() or graph_input
            cleaned_text = graph_output
        else:
            cleaned_text = text

        return cleaned_text

    # Run agents to get the GraphAgent response (expected JSON payload)
    cleaned_or_payload = asyncio.run(run_pipeline(user_text))

    # The GraphAgent is expected to return a JSON payload (string) calling the tool.
    # Try to parse the returned string as JSON. If parsing fails, attempt to extract JSON substring.
    payload_text = cleaned_or_payload.strip()
    parsed = None
    try:
        parsed = json.loads(payload_text)
    except Exception:
        # try to find a JSON object inside the text
        start = payload_text.find("{")
        end = payload_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(payload_text[start:end+1])
            except Exception:
                parsed = None

    if not parsed or "tool" not in parsed:
        # Fallback: assume cleaned_or_payload is cleaned text and call tool directly
        st.warning("Agent did not return a valid tool call payload. Falling back to direct extraction using cleaned text.")
        cleaned_text = cleaned_or_payload
        try:
            graph_documents, rdf_graph = TOOL_REGISTRY["build_from_text"](cleaned_text, model="gpt-4o")
        except Exception as e:
            st.error(f"RDF extraction failed: {e}")
            st.stop()
    else:
        tool_name = parsed.get("tool")
        args = parsed.get("args", {})

        if tool_name not in TOOL_REGISTRY:
            st.error(f"Tool '{tool_name}' is not registered.")
            st.stop()

        # Execute registered tool
        try:
            # call with keyword args
            result = TOOL_REGISTRY[tool_name](**args)
            # build_from_text returns (graph_documents, rdf_graph)
            if isinstance(result, tuple) and len(result) >= 2:
                graph_documents, rdf_graph = result[0], result[1]
            else:
                st.error("Tool did not return expected (graph_documents, rdf_graph).")
                st.stop()
        except Exception as e:
            st.error(f"Tool execution failed: {e}")
            st.stop()

    st.success("RDF extraction completed.")

    # Convert rdflib graph to NetworkX then to PyVis for interactive movable visualization
    nx_graph = nx.DiGraph()
    for s, p, o in rdf_graph:
        # Clean the URIs to get readable labels
        s_label = clean_uri(str(s))
        p_label = clean_uri(str(p))
        o_label = clean_uri(str(o))
        
        # For literals, use their direct string value
        if isinstance(o, Literal):
            o_label = str(o)

        # Add nodes with cleaned labels
        nx_graph.add_node(str(s), label=s_label)
        nx_graph.add_node(str(o), label=o_label)
        nx_graph.add_edge(str(s), str(o), label=p_label)

    if nx_graph.number_of_nodes() == 0:
        st.warning("No nodes extracted into the RDF graph.")
        st.stop()

    net = Network(height="700px", width="100%", directed=True)
    net.from_nx(nx_graph)

    net.set_options(
        """
        var options = {
          "nodes": {"font": {"size": 14}, "scaling": {"min": 10, "max": 30}},
          "edges": {"arrows": {"to": {"enabled": true}}, "smooth": {"type": "continuous"}},
          "physics": {"barnesHut": {"gravitationalConstant": -8000, "springLength": 250}}
        }
        """
    )

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    tmpfile = tmp.name
    tmp.close()
    net.save_graph(tmpfile)

    with st.expander("Cleaned text / agent payload"):
        st.write(payload_text)

    st.markdown("### Interactive RDF Knowledge Graph")
    with open(tmpfile, "r", encoding="utf-8") as f:
        html = f.read()
    components.html(html, height=720, scrolling=True)