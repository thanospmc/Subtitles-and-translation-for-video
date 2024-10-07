## Web app for getting original and translated subtitles for videos

This is a simple web app that uses the [OpenAI Whisper](https://platform.openai.com/docs/guides/speech-to-text) and [DeepL](https://www.deepl.com/en/pro-api/) APIs for generating and translating subtitles for videos in .srt format.

### How to install and use
1. Download the source code or clone the repository and install the requirements
```python
pip install -r requirements.txt
```
2. Install `ffmpeg`
   - On Ubuntu or Debian: `sudo apt-get install ffmpeg`
   - On macOS with Homebrew: `brew install ffmpeg`
   - On Windows, you can download it from the official FFmpeg website and add it to your system PATH.
3. Set up environment variables with your API keys
```bash
OPENAI_API_KEY=your_openai_api_key_here
DEEPL_API_KEY=your_deepl_api_key_here
```
4. Run in terminal
```bash
uvicorn main:app --reload
```
5. Copy the link to a browser to interact with the app
