# Voice Chat Bot Integration - Google Gemini API

## Overview
Successfully integrated Google Gemini API for voice chat functionality in your Python Flask application.

## Files Created/Modified

### 1. Environment Configuration
- **`.env`** - Stores API keys and configuration
- **`requirements.txt`** - Updated dependencies

### 2. Backend Files
- **`app/routes/gemini_chat.py`** - New Flask blueprint with Gemini API integration
- **`app/app.py`** - Modified to register the new blueprint

### 3. Frontend Files  
- **`templates/voice_chat.html`** - Complete voice chat interface with recording functionality

## Setup Instructions

### 1. Configure API Key
Edit the `.env` file and add your Google Gemini API key:
```bash
GEMINI_API_KEY=your_actual_gemini_api_key_here
SECRET_KEY=your_flask_secret_key_here
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python run.py
```

### 4. Access Voice Chat
Open your browser and navigate to: `http://localhost:5001/gemini/`

## Features Implemented

### Backend (Python)
- **Audio Processing**: Accepts WebM/WAV audio files
- **Gemini API Integration**: Transcribes audio and generates responses
- **Chat History**: Maintains conversation context per user session
- **Error Handling**: Comprehensive error responses
- **Security**: API key stored in environment variables

### Frontend (HTML/JavaScript)
- **Voice Recording**: Uses `navigator.mediaDevices.getUserMedia()`
- **Audio Format**: Records in WebM format with Opus codec
- **Real-time UI**: Recording indicator with animation
- **Chat Interface**: Message display with transcription and responses
- **Responsive Design**: Modern gradient UI with smooth animations

## API Endpoints

### Voice Chat
- **POST** `/gemini/chat` - Upload audio and get AI response
- **GET** `/gemini/chat/history` - Get chat history
- **POST** `/gemini/chat/clear` - Clear chat history
- **GET** `/gemini/health` - Check API configuration
- **GET** `/gemini/` - Voice chat interface

## Usage Instructions

1. **Grant Microphone Access**: Click the microphone button and allow browser permissions
2. **Record Message**: Hold the microphone button while speaking
3. **Process Audio**: Release to stop recording and send to Gemini API
4. **View Results**: See transcription and AI response in chat
5. **Continue Conversation**: Multiple messages maintain context

## Security Notes

- API key is loaded from environment variables (`.env` file)
- Temporary audio files are automatically deleted after processing
- Chat sessions are stored in memory (consider Redis/database for production)
- Audio files are validated for type and size

## Technical Specifications

- **Audio Format**: WebM with Opus codec
- **Sample Rate**: 44.1kHz
- **Audio Features**: Echo cancellation, noise suppression
- **Chat History**: Last 20 messages maintained per session
- **Gemini Model**: gemini-1.5-pro
- **System Instruction**: "You are a voice assistant. First transcribe the received audio, then respond to it."

## Troubleshooting

### Common Issues

1. **Microphone Access Denied**
   - Check browser permissions
   - Ensure HTTPS in production

2. **API Key Error**
   - Verify `.env` file configuration
   - Check Gemini API key validity

3. **Audio Processing Failed**
   - Ensure audio format is supported
   - Check file size limits

4. **Connection Issues**
   - Verify Flask server is running
   - Check network connectivity

### Error Messages
- "Gemini API not configured" - Check API key in `.env`
- "Failed to access microphone" - Check browser permissions
- "Invalid file type" - Use supported audio formats

## Production Considerations

1. **Database Storage**: Replace in-memory chat sessions with database
2. **File Storage**: Use cloud storage for audio files
3. **Rate Limiting**: Implement API rate limiting
4. **Authentication**: Add user authentication for chat sessions
5. **Monitoring**: Add logging and error tracking

## Dependencies
```
flask>=2.0.0
google-generativeai>=0.8.0
python-dotenv>=1.0.0
werkzeug>=2.0.0
```
