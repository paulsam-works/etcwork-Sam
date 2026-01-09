import pandas as pd
import spacy
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import json
from openai import OpenAI

client = OpenAI(api_key='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')

def generate_taxonomy(terms):
    # Craft a clear and specific system prompt and user prompt
    system_prompt = """You are an expert taxonomist AI. Your task is to organize a list of terms into a hierarchical taxonomy. Please ensure that the taxonomy is logically structured and relevant to the domain of technology products. 
    The output MUST be a valid JSON object."""
    user_prompt = f"""
    Organize the following terms into a hierarchical taxonomy structure. 
    Terms: {', '.join(terms)}
    
    The output should be a JSON object where the top level is a single root category, and nested objects represent subcategories. Do not include any introductory or concluding text outside the JSON. Ensure a logical structure for a technology products domain.
    """
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo", # or gpt-4 for better results
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"} # Force JSON output
    )
    
    taxonomy_json = response.choices[0].message.content
    return json.loads(taxonomy_json)


#Load english model
nlp = spacy.load("en_core_web_sm")

def extract_terms(text_data, num_terms=50):
    """Processes text data to extract the most common noun phrases."""
    doc = nlp(text_data)
    # Extract noun chunks (good indicators of key topics/terms)
    noun_chunks = [chunk.text.lower() for chunk in doc.noun_chunks if len(chunk.text.split()) > 1]
    
    # Count frequency of terms
    term_counts = Counter(noun_chunks)
    most_common_terms = [term for term, count in term_counts.most_common(num_terms)]
    
    return most_common_terms
def cluster_terms(terms, num_clusters=5):
    """Clusters terms into groups based on semantic similarity using KMeans."""
    # Convert terms into numerical features using TF-IDF
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(terms)
    
    # Apply KMeans clustering
    kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
    kmeans.fit(X)
    
    # Organize terms by their cluster label
    clustered_groups = {}
    for i, term in enumerate(terms):
        label = kmeans.labels_[i]
        if label not in clustered_groups:
            clustered_groups[label] = []
        clustered_groups[label].append(term)
        
    return clustered_groups



# Example Usage:
sample_text = """
The latest iPhone 16 Pro Max was released in September by Apple Inc. It features a new A18 chip and a triple-camera system. 
Competitors like Samsung are also launching new products, such as the Galaxy S25 Ultra. 
The tech market is very competitive, especially in North America and Europe. 
The event took place in San Francisco.
"""
input_file_path = 'medical_devices_tax_doc.txt'
try:
    with open(input_file_path, 'r') as file:
        content = file.read()
        print('content of the file ==============',content)
except FileNotFoundError:
    print(f"Error: The file '{input_file_path}' was not found.")
except Exception as e:
    print(f"An error occurred: {e}")

identified_terms = extract_terms(content)
print(f"Identified Terms: {identified_terms}")


# Example Usage:
#clustered_results = cluster_terms(identified_terms, num_clusters=3)
#print("\nClustered Groups:")
#for cluster_id, terms in clustered_results.items():
 #   print(f"Cluster {cluster_id}: {terms}")

# Generate and print the taxonomy
taxonomy = generate_taxonomy(identified_terms)
print("\nGenerated Taxonomy (JSON):")
print(json.dumps(taxonomy, indent=4))

file_path = 'taxonomy_sample.json'
try:
    with open(file_path, 'w') as json_file:
        json.dump(taxonomy, json_file, indent=4)  # indent=4 for pretty-printing
    print(f"JSON data successfully dumped to '{file_path}'")
except IOError as e:
    print(f"Error writing to file: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")