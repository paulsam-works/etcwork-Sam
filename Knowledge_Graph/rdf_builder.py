from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from dotenv import load_dotenv
import os
from rdflib import Graph, Literal, URIRef, Namespace
from rdflib.namespace import RDF, RDFS, XSD
import streamlit as st
import rdflib
import networkx as nx
import matplotlib.pyplot as plt

load_dotenv()


def get_model_client():
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in environment variables.")
    
    # initialize the llm and transformer for the graph builder.
    model_client = ChatOpenAI(model='gpt-4o', temperature=0, api_key=OPENAI_API_KEY)

    return model_client

def get_rdf_documents():

    # get the model client
    model_client = get_model_client()
    llm_transformer = LLMGraphTransformer(llm=model_client)

    # Example unstructured text data
    text = """
    The Eiffel Tower, located in Paris, was constructed by Gustave Eiffel.
    Construction began in 1887 and it was completed in 1889 for the World's Fair.
    Gustave Eiffel was a French civil engineer and architect.
    """
    documents = [Document(page_content=text)]

    # Use the transformer to generate graph documents
    graph_documents = llm_transformer.convert_to_graph_documents(documents)
    return graph_documents


def build_graph(graph_documents):

    graph_g = Graph()

    # Define namespaces for better organization and readability
    EX = Namespace("http://example.org/ontology/")

    graph_g.bind("ex", EX)
    graph_g.bind("rdf", RDF)
    graph_g.bind("rdfs", RDFS)
    graph_g.bind("xsd", XSD)

    for gd in graph_documents:
        for node in gd.nodes:
            subject = URIRef(EX[node.id.replace(" ", "_")]) # Create a URI for the node
            graph_g.add((subject, RDF.type, EX[node.type])) # Assert its type
            graph_g.add((subject, RDFS.label, Literal(node.id))) # Add a human-readable label

            # Add node properties
            for key, value in node.properties.items():
                predicate = URIRef(EX[key.replace(" ", "_")])
                graph_g.add((subject, predicate, Literal(value)))

    for gd in graph_documents:
        for rel in gd.relationships:
            subject = URIRef(EX[rel.source.id.replace(" ", "_")])
            predicate = URIRef(EX[rel.type.replace(" ", "_")])
            obj = URIRef(EX[rel.target.id.replace(" ", "_")])
            graph_g.add((subject, predicate, obj))

        # Add relationship properties if any
        for key, value in rel.properties.items():
            rel_prop_predicate = URIRef(EX[f"{rel.type.replace(' ', '_')}_{key.replace(' ', '_')}"])
            graph_g.add((subject, rel_prop_predicate, Literal(value)))

    print(graph_g.serialize(format="turtle"))

    # Iterate and print each triple
    print("Triples in the graph:")
    for s, p, o in graph_g:
        print(f"Subject: {s}, Predicate: {p}, Object: {o}")
    return graph_g

def show_graph(graph_g):
    st.title("RDFLib Graph Visualization")

    # Convert RDFLib graph to NetworkX graph
    nx_graph = nx.DiGraph()

    for s, p, o in graph_g:
        nx_graph.add_edge(str(s), str(o), label=str(p))

    # Visualize with Matplotlib
    fig, ax = plt.subplots(figsize=(10, 8))
    pos = nx.spring_layout(nx_graph, k=0.5, iterations=50) # Adjust layout as needed
    nx.draw_networkx_nodes(nx_graph, pos, ax=ax, node_size=3000, node_color="skyblue")
    nx.draw_networkx_edges(nx_graph, pos, ax=ax, arrowstyle="->", arrowsize=20, edge_color="gray")
    nx.draw_networkx_labels(nx_graph, pos, ax=ax, font_size=10)
    edge_labels = nx.get_edge_attributes(nx_graph, 'label')
    nx.draw_networkx_edge_labels(nx_graph, pos, edge_labels=edge_labels, ax=ax, font_size=8)

    st.pyplot(fig)


def main():
    graph_documents = get_rdf_documents()
    graph_g = build_graph(graph_documents)
    show_graph(graph_g)


if __name__ == "__main__":
    main()
