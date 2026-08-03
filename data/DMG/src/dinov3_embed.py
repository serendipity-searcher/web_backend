"""
DINOv3 image embedding extraction for cosine-similarity search.

Produces L2-normalised CLS embeddings for a folder of images, saves them
as a numpy array, and builds a FAISS inner-product index ready for retrieval.

Requirements:
    pip install "transformers>=4.56.0" torch pillow numpy faiss-cpu tqdm

Available ViT checkpoints (ascending size / quality):
    facebook/dinov3-vits16-pretrain-lvd1689m   ~22M params,  ~85MB
    facebook/dinov3-vitb16-pretrain-lvd1689m   ~86M params, ~330MB  ← default
    facebook/dinov3-vitl16-pretrain-lvd1689m  ~304M params, ~1.2GB
    facebook/dinov3-vitg14-pretrain-lvd1689m  ~1.1B params, ~4.3GB  (float16 only on 8GB)
"""

import json
import numpy as np
import torch
import torch.nn.functional as F
import faiss
from pathlib import Path
from PIL import Image
from tqdm import tqdm
from transformers import AutoImageProcessor, AutoModel


# ---------------------------------------------------------------------------
# Configuration — edit here
# ---------------------------------------------------------------------------

IMAGE_DIR   = "./images"
EXTENSIONS  = {".jpg", ".jpeg", ".png", ".webp", ".tiff"}
MODEL_ID    = "facebook/dinov3-vitl16-pretrain-lvd1689m"
BATCH_SIZE  = 16          # lower if you hit RAM limits; 8 is safe on 8GB
DTYPE       = torch.float16   # float32 also works; float16 halves RAM for free
DEVICE      = "cuda" if torch.cuda.is_available() else "cpu"

OUT_DIR     = Path("./dinov3_output")
OUT_DIR.mkdir(exist_ok=True)

EMBEDDINGS_PATH  = OUT_DIR / "embeddings.npy"
PATHS_FILE       = OUT_DIR / "image_paths.json"
FAISS_INDEX_PATH = OUT_DIR / "faiss.index"


# ---------------------------------------------------------------------------
# Load model + processor
# ---------------------------------------------------------------------------

def load_model(model_id: str, dtype: torch.dtype, device: str):
    print(f"Loading {model_id} …")
    processor = AutoImageProcessor.from_pretrained(model_id)
    model = AutoModel.from_pretrained(model_id, torch_dtype=dtype)
    model = model.to(device).eval()

    n_params = sum(p.numel() for p in model.parameters())
    print(f"  Parameters : {n_params / 1e6:.1f}M")
    print(f"  dtype      : {dtype}")
    print(f"  device     : {device}")
    print(f"  hidden_dim : {model.config.hidden_size}")

    # DINOv3 uses register tokens; log how many so we can slice correctly
    n_reg = getattr(model.config, "num_register_tokens", 0)
    print(f"  register tokens: {n_reg}")
    return processor, model


# ---------------------------------------------------------------------------
# Dataset helpers
# ---------------------------------------------------------------------------

def collect_paths(image_dir: str, extensions: set) -> list[Path]:
    paths = [p for p in Path(image_dir).rglob("*") if p.suffix.lower() in extensions]
    if not paths:
        raise FileNotFoundError(f"No images found in {image_dir!r} "
                                f"with extensions {extensions}")
    print(f"Found {len(paths)} images in {image_dir!r}")
    return sorted(paths)


def load_batch(paths: list[Path]) -> list[Image.Image]:
    images = []
    for p in paths:
        try:
            images.append(Image.open(p).convert("RGB"))
        except Exception as e:
            print(f"  Warning: could not open {p}: {e}")
            images.append(None)
    return images


# ---------------------------------------------------------------------------
# Embedding extraction
# ---------------------------------------------------------------------------

@torch.inference_mode()
def extract_embeddings(
    processor,
    model,
    image_paths: list[Path],
    batch_size: int,
    device: str,
    dtype: torch.dtype,
) -> np.ndarray:
    """
    Returns an (N, D) float32 array of L2-normalised CLS embeddings.

    DINOv3's last_hidden_state layout:
        [CLS token | register_tokens... | patch_tokens...]
    We take only the CLS token (index 0) for global image similarity.
    """
    n_reg = getattr(model.config, "num_register_tokens", 0)
    all_embeddings = []
    valid_paths = []

    for i in tqdm(range(0, len(image_paths), batch_size), desc="Embedding"):
        batch_paths = image_paths[i : i + batch_size]
        images = load_batch(batch_paths)

        # Filter out images that failed to load
        good = [(p, img) for p, img in zip(batch_paths, images) if img is not None]
        if not good:
            continue
        batch_paths_good, images_good = zip(*good)

        inputs = processor(images=list(images_good), return_tensors="pt")
        inputs = {k: v.to(device=device, dtype=dtype if v.is_floating_point() else v.dtype)
                  for k, v in inputs.items()}

        outputs = model(**inputs)

        # CLS token is always index 0 in last_hidden_state
        # Shape: (batch, 1 + n_reg + n_patches, hidden_size) → take [:, 0, :]
        cls_tokens = outputs.last_hidden_state[:, 0, :]        # (B, D)

        # L2-normalise → unit hypersphere → cosine sim = dot product
        cls_norm = F.normalize(cls_tokens.float(), dim=-1)     # cast to float32

        all_embeddings.append(cls_norm.cpu().numpy())
        valid_paths.extend(batch_paths_good)

    embeddings = np.concatenate(all_embeddings, axis=0).astype("float32")
    print(f"\nExtracted {len(embeddings)} embeddings of dim {embeddings.shape[1]}")
    return embeddings, list(valid_paths)


# ---------------------------------------------------------------------------
# FAISS index
# ---------------------------------------------------------------------------

def build_index(embeddings: np.ndarray, index_path: Path) -> faiss.Index:
    """
    Flat inner-product index.  Since embeddings are L2-normalised,
    inner product == cosine similarity — exact, no approximation.

    At 30k images this is milliseconds per query and fits in RAM easily.
    """
    d = embeddings.shape[1]
    index = faiss.IndexFlatIP(d)
    # faiss.normalize_L2 is a no-op here since we already normalised,
    # but calling it is a cheap safety guarantee.
    emb_copy = embeddings.copy()
    faiss.normalize_L2(emb_copy)
    index.add(emb_copy)
    faiss.write_index(index, str(index_path))
    print(f"FAISS index: {index.ntotal} vectors, dim={d} → {index_path}")
    return index


# ---------------------------------------------------------------------------
# Querying
# ---------------------------------------------------------------------------

def query(
    index: faiss.Index,
    image_paths: list[Path],
    query_embedding: np.ndarray,
    k: int = 10,
) -> list[tuple[Path, float]]:
    """
    Find k nearest neighbours for a single L2-normalised query embedding.
    Returns list of (path, cosine_similarity) sorted by similarity desc.
    """
    q = query_embedding.reshape(1, -1).astype("float32")
    faiss.normalize_L2(q)
    scores, indices = index.search(q, k)
    return [(image_paths[idx], float(scores[0][j]))
            for j, idx in enumerate(indices[0]) if idx >= 0]


def embed_single_image(
    processor, model, image_path: str, device: str, dtype: torch.dtype
) -> np.ndarray:
    """Embed one image at inference time for live querying."""
    img = Image.open(image_path).convert("RGB")
    inputs = processor(images=[img], return_tensors="pt")
    inputs = {k: v.to(device=device, dtype=dtype if v.is_floating_point() else v.dtype)
              for k, v in inputs.items()}
    with torch.inference_mode():
        outputs = model(**inputs)
    cls = outputs.last_hidden_state[:, 0, :]
    return F.normalize(cls.float(), dim=-1).squeeze(0).cpu().numpy()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 1. Load model
    processor, model = load_model(MODEL_ID, DTYPE, DEVICE)

    # 2. Collect image paths
    image_paths = collect_paths(IMAGE_DIR, EXTENSIONS)

    # 3. Extract embeddings
    embeddings, valid_paths = extract_embeddings(
        processor, model, image_paths, BATCH_SIZE, DEVICE, DTYPE
    )

    # 4. Save embeddings + path index
    np.save(EMBEDDINGS_PATH, embeddings)
    with open(PATHS_FILE, "w") as f:
        json.dump([str(p) for p in valid_paths], f, indent=2)
    print(f"Saved embeddings → {EMBEDDINGS_PATH}")
    print(f"Saved path index → {PATHS_FILE}")

    # 5. Build FAISS index
    index = build_index(embeddings, FAISS_INDEX_PATH)

    # 6. Example: query with the first image and print top-5 neighbours
    print("\n--- Example query: top-5 neighbours of images[0] ---")
    results = query(index, valid_paths, embeddings[0], k=6)
    for rank, (path, score) in enumerate(results):
        print(f"  {rank}. {score:.4f}  {path}")


# ---------------------------------------------------------------------------
# Reload and query later (without re-embedding)
# ---------------------------------------------------------------------------
# index = faiss.read_index(str(FAISS_INDEX_PATH))
# with open(PATHS_FILE) as f:
#     image_paths = [Path(p) for p in json.load(f)]
# q_emb = embed_single_image(processor, model, "path/to/query.jpg", DEVICE, DTYPE)
# results = query(index, image_paths, q_emb, k=10)
