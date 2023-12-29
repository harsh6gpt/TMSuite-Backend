import os
import torch
import torchvision.transforms as T
from PIL import Image
from clip import load
import pandas as pd
import chromadb
from multiprocessing import Pool
import uuid
from tqdm import tqdm


# Step 1: Load the CLIP model
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = load("ViT-B/16", device)
chroma_client = chromadb.Client()

# Step 2: Embedding Function
def generate_image_embedding(image_paths_list):
    image_embeddings = []
    for path in tqdm(image_paths_list):
        try:
            # Load and preprocess the image
            image = Image.open(path).convert("RGB")
            image_input = preprocess(image).unsqueeze(0).to(device)
            # Generate embedding
            with torch.no_grad():
                image_embedding = model.encode_image(image_input)
            image_embedding = [item.item() for item in image_embedding.cpu().numpy().flatten()]
            image_embeddings.append({'Application Number': int(os.path.basename(path).split('_')[0]), 'Embedding': image_embedding})
        except:
            continue

    df = pd.DataFrame.from_records(image_embeddings)
    image_dir = os.path.basename(os.path.dirname(image_paths_list[0]))
    image_dir = image_dir + '_embeddings'
    filename = str(uuid.uuid4()) + '.csv'
    df.to_csv(os.path.join(image_dir, filename))
    return



# Step 3: Search for similar images based on query and filter
def search_images(query_image_path, class_filter='ALL'):
    collection = chroma_client.get_collection(name='visual_search')

    # Load and preprocess the query image
    query_image = Image.open(query_image_path).convert("RGB")
    query_image_input = preprocess(query_image).unsqueeze(0).to(device)

    # Generate embedding for the query image
    with torch.no_grad():
        query_embedding = model.encode_image(query_image_input)

    query_embedding = [item.item() for item in query_embedding.cpu().numpy().flatten()]

    # Search for similar images
    if class_filter == 'ALL':
        results = collection.query(query_embeddings=[query_embedding], n_results=10)
    else:
        results = collection.query(query_embeddings=[query_embedding], n_results=10, where={"Class": {"$in" : class_filter}})
    return results


def refine_search_results(image_search_results, query_application_numbers):
    output = {}
    for index, item in enumerate(image_search_results['ids']):
        output[query_application_numbers[index]] = [(image_search_results['ids'][index][new_index], image_search_results['distances'][index][new_index]) for new_index, app in enumerate(image_search_results['ids'][index]) if app != query_application_numbers[index]]
    return output
