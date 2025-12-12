# Domain Classifier Training

This folder contains everything needed to train a domain classifier for Galatea's intelligent model routing.

## Quick Start

```bash
# 1. Install dependencies
pip install sentence-transformers scikit-learn numpy

# 2. Run training
python train_classifier.py

# 3. Copy model to backend (optional - pattern matching works without it)
cp domain_classifier.pkl ../backend/app/services/
```

## Files

| File | Description |
|------|-------------|
| `domain_classifier_train.jsonl` | Training data (200+ labeled examples) |
| `train_classifier.py` | Training script with evaluation |
| `domain_classifier.pkl` | Output model (created after training) |

## Training Data Format

JSONL format with `text` and `domain` fields:

```json
{"text": "What are the side effects of metformin?", "domain": "medical"}
{"text": "Can I sue my landlord for not fixing the heating?", "domain": "legal"}
{"text": "How do I reverse a linked list in Python?", "domain": "coding"}
```

## Supported Domains

| Domain | Description | Specialist Model |
|--------|-------------|------------------|
| `general` | Everyday questions, chat | (default model) |
| `medical` | Health, symptoms, medications | meditron:7b |
| `legal` | Law, contracts, rights | saul-instruct:7b |
| `coding` | Programming, debugging | qwen2.5-coder:7b |
| `math` | Calculations, equations | mathstral:7b |
| `finance` | Investing, taxes, budgeting | (disabled by default) |

## Adding More Training Data

To improve accuracy:

1. Add more examples to `domain_classifier_train.jsonl`
2. Aim for 50+ examples per domain
3. Include edge cases and ambiguous queries
4. Re-run training

### Generating Synthetic Data

You can use a large LLM to generate more training data:

```
Generate 50 questions a patient might ask their doctor.
Each question should be a single sentence.
Format: one question per line.
```

Then convert to JSONL:
```python
questions = open("medical_questions.txt").readlines()
for q in questions:
    print(json.dumps({"text": q.strip(), "domain": "medical"}))
```

## Model Architecture

The classifier uses:
- **Embeddings**: `all-MiniLM-L6-v2` (22M params, ~100MB)
- **Classifier**: Logistic Regression (multinomial)
- **Total size**: ~100MB

This is small enough to load alongside the main LLM without impacting VRAM.

## Expected Performance

With the provided training data:
- **Accuracy**: ~90-95%
- **Inference time**: <10ms per query
- **Memory**: ~200MB (including embedding model)

## Integration with Galatea

The trained classifier can be used in `domain_router.py`:

```python
from .domain_classifier import DomainClassifier

classifier = DomainClassifier.load("domain_classifier.pkl")
domain, confidence = classifier.predict("What causes diabetes?")
# domain = "medical", confidence = 0.92
```

However, the current pattern-matching approach works well for most cases.
The classifier is an optimization for edge cases and ambiguous queries.

