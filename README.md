# Medical Error Analysis

A Streamlit application to analyze errors in medical images.

## Structure

The project is organized to separate the UI logic, data inputs, and documentation resources.

```text
├── app.py                  # Main Streamlit application (UI, authentication, and workflow).
├── utils.py                # Backend utilities (Google Sheets connection and data saving).
├── requirements.txt        # Project dependencies.
├── data/                   # Evaluation inputs.
│   ├── imagenes/           # Structured medical images corresponding to questions.
│   └── preguntas-respuestas/ # JSONL files per model containing the QA pairs to be audited.
├── extra/                  # Documentation resources (e.g., user guide).
└── old/                    # Archive of previous app versions.
```

### Key Components

| Component | Description |
| :--- | :--- |
| **`app.py`** | **Main Entry Point.** Handles user login, renders medical cases, and manages the error categorization interface. |
| **`utils.py`** | **Backend Operations.** Manages the connection to Google Sheets to save expert annotations and track progress. |
| **`data/preguntas-respuestas/`** | **Model Outputs.** Stores JSONL files containing questions and answers for each specific model. |
| **`data/imagenes/`** | **Diagnostic Assets.** Contains the medical images corresponding to the questions, organized by category. |
| **`extra/`** | **Documentation.** Includes support materials, such as the `guia.md` for medical evaluators. |

## Dependencies
streamlit 1.29.0  
pandas 2.2.2  
gspread 6.1.2  
google-auth 2.23.4  
google-auth-oauthlib 1.1.0  

## Installation

To install the dependencies, run the following command:

```bash
pip install -r requirements.txt
```

## Running the Application

To run the application, use the following command:

```bash
streamlit run app.py
```

## Deployment

To deploy the application on Streamlit Community Cloud:

1.  Upload this repository to your GitHub account.
2.  Go to [Streamlit Community Cloud](https://share.streamlit.io/).
3.  Click on "New app" and select the repository you just created.
4.  Make sure the main branch and the `app.py` file are selected.
5.  Click "Deploy!".
