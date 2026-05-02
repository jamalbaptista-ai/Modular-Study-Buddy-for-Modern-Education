from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import Settings
from src.openai_client import StudyCompanionClient
from src.progress_manager import ProgressManager
from src.ui_helpers import download_progress, list_local_files, save_files


st.set_page_config(page_title="Adaptive AI Study Companion", page_icon="📘", layout="wide")

st.title("📘 Adaptive AI Study Companion")
st.caption("Adaptive quizzes, file-grounded study help, local fallback retrieval, progress tracking, and spaced review.")


try:
    settings = Settings.from_env()
except Exception as error:
    st.error(str(error))
    st.stop()


client = StudyCompanionClient(
    api_key=settings.openai_api_key,
    model_name=settings.model_name,
    uploads_dir=settings.uploads_dir,
)

progress = ProgressManager(settings.app_data_dir / "student_progress.json")


# -----------------------------
# Session State
# -----------------------------
if "vector_store_id" not in st.session_state:
    st.session_state.vector_store_id = None

if "uploaded_names" not in st.session_state:
    st.session_state.uploaded_names = list_local_files(settings.uploads_dir)

if "previous_response_id" not in st.session_state:
    st.session_state.previous_response_id = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "latest_question" not in st.session_state:
    st.session_state.latest_question = None

if "latest_question_context_source" not in st.session_state:
    st.session_state.latest_question_context_source = None

if "latest_result" not in st.session_state:
    st.session_state.latest_result = None

if "flashcards" not in st.session_state:
    st.session_state.flashcards = []

if "flashcard_context_source" not in st.session_state:
    st.session_state.flashcard_context_source = None

if "flashcard_difficulty_mode" not in st.session_state:
    st.session_state.flashcard_difficulty_mode = "Automatic"

if "flashcard_difficulty_used" not in st.session_state:
    st.session_state.flashcard_difficulty_used = None

if "quiz_variation_id" not in st.session_state:
    st.session_state.quiz_variation_id = 0

if "quiz_question_history" not in st.session_state:
    st.session_state.quiz_question_history = []

if "answer_box_id" not in st.session_state:
    st.session_state.answer_box_id = 0

if "flashcard_variation_id" not in st.session_state:
    st.session_state.flashcard_variation_id = 0

if "flashcard_front_history" not in st.session_state:
    st.session_state.flashcard_front_history = []


# -----------------------------
# Header Metrics
# -----------------------------
snapshot = progress.snapshot()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Attempts", snapshot["total_attempts"])
col2.metric("Correct", snapshot["total_correct"])
col3.metric("Accuracy", f"{snapshot['overall_accuracy']:.1%}")
col4.metric("Model", settings.model_name)


tabs = st.tabs([
    "Setup & Documents",
    "Chat",
    "Adaptive Quiz",
    "Flashcards",
    "Progress Dashboard",
    "Weekly Report",
    "Debug",
])


# -----------------------------
# Setup & Documents
# -----------------------------
with tabs[0]:
    st.subheader("Setup & Documents")

    st.write(
        "The app supports two document modes: vector store retrieval and local-file fallback."
    )

    uploaded_files = st.file_uploader(
        "Upload study materials",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Save Files Only"):
            if not uploaded_files:
                st.warning("Upload at least one file first.")
            else:
                saved = save_files(uploaded_files, settings.uploads_dir)
                st.session_state.uploaded_names = list_local_files(settings.uploads_dir)
                st.success(f"Saved {len(saved)} file(s). Local fallback is now available.")

    with col2:
        if st.button("Save Files and Create Vector Store"):
            if not uploaded_files:
                st.warning("Upload at least one file first.")
            else:
                saved = save_files(uploaded_files, settings.uploads_dir)
                st.session_state.uploaded_names = list_local_files(settings.uploads_dir)

                with st.spinner("Saving files and creating vector store..."):
                    st.session_state.vector_store_id = client.create_vector_store(saved)

                st.success("Files saved and vector store created. Chat can now use vector retrieval.")
                st.code(st.session_state.vector_store_id)

    st.write("### Current document status")

    local_files = list_local_files(settings.uploads_dir)
    st.write("Local saved files:", local_files or "None")
    st.write("Vector store ID:", st.session_state.vector_store_id or "None")

    if st.session_state.vector_store_id:
        st.success("Primary retrieval mode: vector store")
    elif local_files:
        st.info("Primary retrieval mode: local-file fallback")
    else:
        st.warning("No uploaded documents are available yet.")


# -----------------------------
# Chat
# -----------------------------
with tabs[1]:
    st.subheader("Chat")

    if st.session_state.vector_store_id:
        st.success("Chat will use vector store retrieval.")
    elif list_local_files(settings.uploads_dir):
        st.info("Chat will use local saved files as fallback context.")
    else:
        st.warning("No study files found. Chat will answer generally.")

    for item in st.session_state.chat_history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])

    user_message = st.chat_input("Ask a study question...")

    if user_message:
        st.session_state.chat_history.append({"role": "user", "content": user_message})

        with st.chat_message("user"):
            st.markdown(user_message)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer, response_id, context_source = client.chat(
                    user_message,
                    st.session_state.previous_response_id,
                    st.session_state.vector_store_id,
                )

            st.session_state.previous_response_id = response_id
            st.markdown(answer)
            st.caption(f"Context source used: {context_source}")

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": answer + f"\n\n_Context source used: {context_source}_",
        })


# -----------------------------
# Adaptive Quiz
# -----------------------------
with tabs[2]:
    st.subheader("Adaptive Quiz")

    snapshot = progress.snapshot()
    recommended_topic = snapshot.get("recommended_topic") or "general course concepts"

    topic = st.text_input("Topic", value=recommended_topic)

    difficulty_mode = st.radio(
        "Difficulty mode",
        ["Automatic", "Manual"],
        horizontal=True,
        help=(
            "Automatic uses your saved progress to choose the difficulty. "
            "Manual lets you choose easy, medium, or hard yourself."
        ),
    )

    automatic_difficulty = progress.get_next_difficulty(topic)

    if difficulty_mode == "Automatic":
        selected_difficulty = automatic_difficulty
        st.info(f"Automatic difficulty for **{topic}**: **{selected_difficulty}**")
    else:
        selected_difficulty = st.selectbox(
            "Choose difficulty",
            ["easy", "medium", "hard"],
            index=["easy", "medium", "hard"].index(automatic_difficulty)
            if automatic_difficulty in ["easy", "medium", "hard"]
            else 0,
        )
        st.info(
            f"Manual difficulty selected: **{selected_difficulty}**. "
            f"The app will still track progress in the background."
        )

    question_type = st.selectbox(
        "Preferred question type",
        ["short_answer", "multiple_choice", "true_false"],
    )

    def generate_new_quiz_question() -> None:
        """Generate a new quiz question and create a fresh answer box."""
        st.session_state.quiz_variation_id += 1
        st.session_state.answer_box_id += 1

        question, context_source = client.generate_quiz(
            topic=topic,
            difficulty=selected_difficulty,
            question_type=question_type,
            vector_store_id=st.session_state.vector_store_id,
            variation_id=st.session_state.quiz_variation_id,
            avoid_previous_questions=st.session_state.quiz_question_history,
        )

        st.session_state.latest_question = question
        st.session_state.latest_question_context_source = context_source
        st.session_state.latest_result = None

        if question.question not in st.session_state.quiz_question_history:
            st.session_state.quiz_question_history.append(question.question)

    st.write("### Question Controls")
    q_col1, q_col2, q_col3 = st.columns(3)

    with q_col1:
        if st.button("Generate New Question"):
            with st.spinner("Generating a new question..."):
                generate_new_quiz_question()

    with q_col2:
        if st.button("Regenerate Different Question"):
            with st.spinner("Generating a different question..."):
                generate_new_quiz_question()

    with q_col3:
        if st.button("Clear Current Question"):
            st.session_state.latest_question = None
            st.session_state.latest_question_context_source = None
            st.session_state.latest_result = None
            st.session_state.answer_box_id += 1

    q = st.session_state.latest_question

    if q:
        st.markdown("### Current Question")
        st.write(f"**Topic:** {q.topic}")
        st.write(f"**Difficulty:** {q.difficulty}")
        st.write(f"**Question type:** {q.question_type}")
        st.write(q.question)

        if q.choices:
            for index, choice in enumerate(q.choices, start=1):
                st.write(f"{index}. {choice}")

        st.caption(f"Context source used: {st.session_state.latest_question_context_source}")

        with st.expander("Source hint"):
            st.write(q.source_hint)

        answer_key = f"student_answer_{st.session_state.answer_box_id}"
        answer = st.text_area(
            "Your answer",
            key=answer_key,
            placeholder="Type your answer here, then click Grade Answer.",
        )

        g_col1, g_col2 = st.columns(2)

        with g_col1:
            if st.button("Grade Answer"):
                if not answer.strip():
                    st.warning("Type your answer first.")
                else:
                    with st.spinner("Grading..."):
                        result = client.grade_answer(q, answer)

                    next_difficulty = progress.update_progress_and_adjust_difficulty(
                        topic=result.topic,
                        difficulty=result.difficulty,
                        is_correct=result.is_correct,
                        score=result.score,
                        question=q.question,
                        user_answer=answer,
                        ideal_answer=result.ideal_answer,
                        feedback=result.feedback,
                    )

                    st.session_state.latest_result = {
                        "is_correct": result.is_correct,
                        "score": result.score,
                        "feedback": result.feedback,
                        "ideal_answer": result.ideal_answer,
                        "next_difficulty": next_difficulty,
                        "difficulty_mode": difficulty_mode,
                    }

        with g_col2:
            if st.button("Continue to Next Question"):
                with st.spinner("Generating the next question..."):
                    generate_new_quiz_question()

    if st.session_state.latest_result:
        result = st.session_state.latest_result

        st.markdown("### Result")

        if result["is_correct"]:
            st.success("Correct!")
        else:
            st.error("Not quite.")

        st.write(f"**Score:** {result['score']:.2f}")
        st.write(f"**Feedback:** {result['feedback']}")
        st.write(f"**Ideal answer:** {result['ideal_answer']}")

        if result["difficulty_mode"] == "Automatic":
            st.info(f"Next automatic difficulty for this topic: **{result['next_difficulty']}**")
        else:
            st.info(
                f"Progress updated. If you switch to Automatic, the next recommended "
                f"difficulty for this topic will be **{result['next_difficulty']}**."
            )

    if st.session_state.quiz_question_history:
        with st.expander("Previously generated questions this session"):
            for index, previous_question in enumerate(st.session_state.quiz_question_history, start=1):
                st.write(f"{index}. {previous_question}")


# -----------------------------
# Flashcards
# -----------------------------
with tabs[3]:
    st.subheader("Flashcards")

    flash_topic = st.text_input(
        "Flashcard topic",
        value=snapshot.get("recommended_topic") or "general course concepts",
    )

    flashcard_difficulty_mode = st.radio(
        "Flashcard difficulty mode",
        ["Automatic", "Manual"],
        horizontal=True,
        help=(
            "Automatic uses your saved quiz progress to choose flashcard difficulty. "
            "Manual lets you choose easy, medium, or hard yourself."
        ),
    )

    automatic_flash_difficulty = progress.get_next_difficulty(flash_topic)

    if flashcard_difficulty_mode == "Automatic":
        flash_difficulty = automatic_flash_difficulty
        st.info(f"Automatic flashcard difficulty for **{flash_topic}**: **{flash_difficulty}**")
    else:
        flash_difficulty = st.selectbox(
            "Choose flashcard difficulty",
            ["easy", "medium", "hard"],
            index=["easy", "medium", "hard"].index(automatic_flash_difficulty)
            if automatic_flash_difficulty in ["easy", "medium", "hard"]
            else 0,
        )
        st.info(
            f"Manual flashcard difficulty selected: **{flash_difficulty}**. "
            f"This does not change your saved quiz progress."
        )

    count = st.slider("Number of flashcards", 3, 10, 5)

    def generate_flashcard_batch(add_to_existing: bool) -> None:
        """Generate flashcards. Either replace existing cards or append more."""
        st.session_state.flashcard_variation_id += 1

        batch, context_source = client.generate_flashcards(
            topic=flash_topic,
            difficulty=flash_difficulty,
            count=count,
            vector_store_id=st.session_state.vector_store_id,
            variation_id=st.session_state.flashcard_variation_id,
            avoid_previous_fronts=st.session_state.flashcard_front_history,
        )

        new_cards = batch.flashcards

        if add_to_existing:
            st.session_state.flashcards.extend(new_cards)
        else:
            st.session_state.flashcards = new_cards

        st.session_state.flashcard_context_source = context_source
        st.session_state.flashcard_difficulty_mode = flashcard_difficulty_mode
        st.session_state.flashcard_difficulty_used = flash_difficulty

        for card in new_cards:
            if card.front not in st.session_state.flashcard_front_history:
                st.session_state.flashcard_front_history.append(card.front)

    st.write("### Flashcard Controls")
    f_col1, f_col2, f_col3 = st.columns(3)

    with f_col1:
        if st.button("Generate New Flashcards"):
            with st.spinner("Generating flashcards..."):
                generate_flashcard_batch(add_to_existing=False)

    with f_col2:
        if st.button("Add More Flashcards"):
            with st.spinner("Adding more flashcards..."):
                generate_flashcard_batch(add_to_existing=True)

    with f_col3:
        if st.button("Clear Flashcards"):
            st.session_state.flashcards = []
            st.session_state.flashcard_context_source = None
            st.session_state.flashcard_difficulty_used = None

    if st.session_state.flashcards:
        st.caption(f"Context source used: {st.session_state.flashcard_context_source}")
        st.caption(
            f"Difficulty mode: {st.session_state.get('flashcard_difficulty_mode', 'Automatic')} | "
            f"Difficulty used: {st.session_state.get('flashcard_difficulty_used', 'easy')}"
        )

        for index, card in enumerate(st.session_state.flashcards, start=1):
            with st.expander(f"Flashcard {index}: {card.front}"):
                st.write(card.back)
                st.caption(f"{card.topic} | {card.difficulty}")

    if st.session_state.flashcard_front_history:
        with st.expander("Previously generated flashcard fronts this session"):
            for index, front in enumerate(st.session_state.flashcard_front_history, start=1):
                st.write(f"{index}. {front}")


# -----------------------------
# Progress Dashboard
# -----------------------------
with tabs[4]:
    st.subheader("Progress Dashboard")

    snapshot = progress.snapshot()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Attempts", snapshot["total_attempts"])
    col2.metric("Total Correct", snapshot["total_correct"])
    col3.metric("Overall Accuracy", f"{snapshot['overall_accuracy']:.1%}")

    if snapshot["due_review_topics"]:
        st.warning("Due for review: " + ", ".join(snapshot["due_review_topics"]))
    else:
        st.success("No topics are due for review right now.")

    rows = snapshot["topic_rows"]

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

        st.write("### Accuracy by Topic")
        st.bar_chart(df.set_index("topic")["accuracy"])

        st.write("### Attempts by Topic")
        st.bar_chart(df.set_index("topic")["attempts"])
    else:
        st.info("Answer quiz questions to create progress data.")

    st.write("### Recent History")

    if snapshot["recent_history"]:
        st.dataframe(pd.DataFrame(snapshot["recent_history"]), use_container_width=True)
    else:
        st.info("No quiz history yet.")

    download_progress(progress.data)

    with st.expander("Reset progress"):
        st.warning("This deletes all saved quiz progress.")

        if st.button("Reset All Progress"):
            progress.reset()
            st.success("Progress reset. Refresh the app.")


# -----------------------------
# Weekly Report
# -----------------------------
with tabs[5]:
    st.subheader("Weekly Report")

    if st.button("Generate Weekly Report"):
        snapshot = progress.snapshot()

        if snapshot["total_attempts"] == 0:
            st.warning("Answer at least one quiz question first.")
        else:
            with st.spinner("Generating report..."):
                report = client.weekly_report(snapshot)

            st.write("### Summary")
            st.write(report.overall_summary)

            st.write("### Strongest Topics")
            for item in report.strongest_topics:
                st.write(f"- {item}")

            st.write("### Weakest Topics")
            for item in report.weakest_topics:
                st.write(f"- {item}")

            st.write("### Review Now")
            for item in report.review_now_topics:
                st.write(f"- {item}")

            st.write("### Recommended Next Focus")
            st.write(report.recommended_next_focus)

            st.write("### Improvement Tip")
            st.write(report.improvement_tip)


# -----------------------------
# Debug
# -----------------------------
with tabs[6]:
    st.subheader("Debug")

    st.write("Use this tab if your API key, files, or retrieval mode are not working.")

    st.write("Base folder:", str(settings.base_dir))
    st.write(".env path:", str(settings.env_path))
    st.write(".env exists:", settings.env_path.exists())
    st.write("Loaded API key:", settings.masked_key())
    st.write("Key starts with sk-:", settings.openai_api_key.startswith("sk-"))
    st.write("Vector store ID:", st.session_state.vector_store_id or "None")
    st.write("Local uploaded files:", list_local_files(settings.uploads_dir) or "None")

    if st.session_state.vector_store_id:
        st.success("Retrieval mode: vector store")
    elif list_local_files(settings.uploads_dir):
        st.info("Retrieval mode: local-file fallback")
    else:
        st.warning("Retrieval mode: no documents")

    st.write("PowerShell commands for API-key troubleshooting:")
    st.code("echo $env:OPENAI_API_KEY", language="powershell")
    st.code("Remove-Item Env:OPENAI_API_KEY", language="powershell")
