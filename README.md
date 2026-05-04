# Adaptive AI Study Companion

## 📌 Overview

The Adaptive AI Study Companion is a personalized learning system that goes beyond traditional chatbots by incorporating persistent memory, adaptive learning, and retrieval-augmented generation (RAG).

Unlike standard LLM tools, this system tracks user performance over time and dynamically adjusts question difficulty to optimize learning.

---

## 🚀 Features

### 📄 Document-Based Learning (RAG)

* Upload study materials (PDFs, notes, etc.)
* Uses vector store or local file retrieval
* Generates context-aware responses

### 🧠 Adaptive Quiz System

* Generates quiz questions using LLM
* Supports:

  * Automatic difficulty (based on performance)
  * Manual difficulty selection
* Allows:

  * Generate new questions
  * Regenerate different questions
  * Continue to next question

### 🧾 Flashcards

* Generate flashcards from uploaded content
* Supports:

  * Automatic difficulty
  * Manual difficulty
  * Add more flashcards dynamically

### 📊 Persistent Memory System

* Stores user performance in JSON
* Tracks:

  * Attempts
  * Accuracy
  * Streaks
  * Difficulty progression

### 🔁 Adaptive Learning Engine

* Adjusts difficulty using:

  * Accuracy thresholds
  * Performance trends
* Prioritizes weak topics

---

## 🧠 Key Innovation

This system transforms a **stateless LLM into a stateful learning system** by:

* Separating memory from the LLM
* Persisting user performance data
* Using stored data to influence future outputs

---

## 🏗️ System Architecture

Pipeline:
User → Upload Docs → Vector Store / Local Files → LLM → Quiz/Chat

Adaptive Loop:
Evaluation → JSON Memory → Adaptive Engine → Adjusted Difficulty

---

## ⚙️ Technologies Used

* OpenAI Responses API
* Python
* Streamlit
* JSON (persistent storage)
* Vector Store (RAG)

---

## ▶️ How to Run

### 1. Create virtual environment

```bash
python -m venv .venv
```

### 2. Activate environment

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set API Key

Create a `.env` file:

```
OPENAI_API_KEY=your_api_key_here
```

### 5. Run app

```bash
streamlit run app.py
```

---

## 📊 Example Memory Structure

```json
{
  "topics": {
    "math": {
      "attempts": 5,
      "correct": 3,
      "accuracy": 0.6,
      "current_difficulty": "medium",
      "streak": 2
    }
  }
}
```

---

## ⚠️ Challenges

* Managing Streamlit session state
* Implementing persistent memory
* Avoiding repeated question generation
* Handling local vs vector retrieval

---
