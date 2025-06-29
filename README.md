# Transcribe Anywhere

A desktop voice-to-text transcription application that allows you to record audio and get instant AI-powered transcriptions using OpenAI's speech-to-text API.

## Features

- 🎤 Record audio with a simple GUI or hotkey (Ctrl+Shift+R)
- 🤖 AI-powered transcription using OpenAI's advanced speech recognition
- 📋 Automatic clipboard copying of transcripts
- ⏱️ Real-time recording timer
- 🖥️ Clean, user-friendly desktop interface
- 🔥 Global hotkey support for quick recording

## Requirements

- Python 3.7+
- OpenAI API key
- Microphone

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/Transcribe-Anywhare.git
   cd Transcribe-Anywhare
   ```

2. Install dependencies:

   **Using pip:**
   ```bash
   pip install -r requirements.txt
   ```

   **Using uv (recommended for faster installation):**
   ```bash
   uv pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   MODEL_NAME=gpt-4o-mini-transcribe
   ```

4. (Optional) Create a `reference.yml` file in the project root for transcription context:
   ```yaml
   terminology:
     API: Application Programming Interface
     ML: Machine Learning
     AI: Artificial Intelligence
   context: "Technical discussion about software development"
   style: "Use formal language and technical terms"
   ```

## Usage

1. Run the application:
   ```bash
   python main.py
   ```

2. Use the GUI buttons or press **Ctrl+Shift+R** to start/stop recording

3. Your transcription will appear in the text area and be automatically copied to your clipboard

## Configuration

### Environment Variables (.env)
- **OPENAI_API_KEY**: Your OpenAI API key (required)
- **MODEL_NAME**: OpenAI model to use (default: gpt-4o-mini-transcribe)

### Reference File (reference.yml)
Optional YAML file to provide context for better transcription accuracy:

- **terminology**: Key-value pairs of technical terms and their definitions
- **context**: Description of the conversation context or domain
- **style**: Preferred transcription style (formal, casual, technical, etc.)

The application automatically loads `reference.yml` from the project root if present.

## Technical Details

- **GUI Framework**: PySimpleGUI with DarkGrey5 theme
- **Audio Recording**: PyAudio for cross-platform audio capture
- **Transcription**: OpenAI API `/v1/audio/transcriptions` endpoint
- **Hotkey Support**: Global keyboard shortcuts using the `keyboard` library

## Troubleshooting

- **No microphone access**: Check system permissions for microphone access
- **Hotkey not working**: On Linux, may require running with elevated permissions
- **API errors**: Verify your OpenAI API key is valid and has sufficient credits