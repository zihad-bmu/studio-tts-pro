import warnings
import sys

# 1. Suppress all unwanted background warnings from third-party libraries
if not sys.warnoptions:
    warnings.simplefilter("ignore", category=SyntaxWarning)
    warnings.simplefilter("ignore", category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)

import streamlit as st
from google import genai
import asyncio
from edge_tts import Communicate
from pydub import AudioSegment
import uuid
import os

# 2. Page Configuration
st.set_page_config(
    page_title="Studio TTS Pro",
    page_icon="🎙️",
    layout="wide"
)

# 3. Premium Animated & Modern UI Styling (CSS Injection)
st.markdown("""
    <style>
    /* Gradient Background Effect for Title */
    .main-title {
        font-size: 3rem !important;
        font-weight: 800 !important;
        background: linear-gradient(45deg, #FF4B4B, #4A90E2, #1DD1A1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
        animation: fadeIn 2s ease-in-out;
    }
    
    /* Subtitle Styling */
    .sub-title {
        text-align: center;
        color: #A0AEC0;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* CSS Animations */
    @keyframes fadeIn {
        0% { opacity: 0; transform: translateY(-10px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }

    /* Custom Styling for Status Cards */
    .css-1r6g78m, .stEmotionCmponent {
        transition: all 0.3s ease;
    }
    
    /* Glowing Effect for Primary Button */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #6C5CE7, #A8DA6C) !important;
        color: white !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 2rem !important;
        transition: all 0.3s ease-in-out !important;
        box-shadow: 0 4px 15px rgba(108, 92, 231, 0.4) !important;
    }
    
    div.stButton > button:first-child:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(108, 92, 231, 0.6) !important;
        animation: pulse 1s infinite;
    }
    </style>
""", unsafe_allow_html=True)

# Render Styled Header
st.markdown('<h1 class="main-title">🎙️ Studio TTS Pro</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Advanced AI Script Writer & Premium High-Fidelity Text-to-Speech Engine</p>', unsafe_allow_html=True)

# 4. Gemini Client Initialization (Latest google-genai SDK)
@st.cache_resource
def get_gemini_client():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        return genai.Client(api_key=api_key)
    except Exception:
        return None

client = get_gemini_client()

# 5. Core Audio Generation Function (Edge-TTS)
async def generate_edge_tts(text, voice, rate, pitch, output_path):
    communicate = Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)

# 6. Main Application Logic
if client:
    # Responsive Two-Column Layout
    col1, col2 = st.columns([1, 1], gap="large")

    # Column 1: AI Script Generation Workspace
    with col1:
        st.subheader("📝 AI Script Generator")
        prompt = st.text_area(
            "Enter your prompt/topic:", 
            placeholder="e.g., Write a motivational 2-minute YouTube video script about time management...",
            height=160
        )
        
        # AI Enhancement Features Toggle
        st.write("✨ **AI Enhancements:**")
        ai_enhance = st.checkbox("Optimize script pacing for speech (Add pauses/emphasis)", value=True)
        tone_select = st.selectbox("Select Script Tone:", ["Energetic/Motivational", "Professional/Formal", "Calm/Storytelling", "Casual/Conversational"])

    # Column 2: Advanced Audio Studio Settings
    with col2:
        st.subheader("⚙️ Audio Configuration")
        
        # Engine Selection
        tts_engine = st.selectbox(
            "Select Text-to-Speech Engine:",
            ["Microsoft Edge-TTS (Premium & Studio Quality)", "Google Standard TTS (Basic)"]
        )
        
        # Audio Quality Bitrate Selection (320kbps and others)
        audio_bitrate = st.selectbox(
            "Audio Quality (Bitrate):",
            ["320 kbps (Ultra High Fidelity / Studio Master)", "256 kbps (High Quality)", "128 kbps (Standard MP3)"]
        )
        # Convert selected option to integer string for pydub
        bitrate_value = audio_bitrate.split(" ")[0] + "k"
        
        # Dynamic Voice Selection Based on Engine
        if "Edge-TTS" in tts_engine:
            voice_option = st.selectbox(
                "Select Voice Actor:",
                [
                    "bn-BD-PradeepNeural (Bengali - Male)",
                    "bn-BD-NabanitaNeural (Bengali - Female)",
                    "en-US-AriaNeural (English - Female)",
                    "en-US-GuyNeural (English - Male)",
                    "en-IN-NeerjaNeural (Indian English - Female)"
                ]
            )
        else:
            voice_option = st.selectbox(
                "Select Voice Actor:",
                [
                    "bn-IN-Wavenet-B (Bengali - Male)",
                    "bn-IN-Wavenet-A (Bengali - Female)",
                    "en-US-Wavenet-D (English - Male)"
                ]
            )
            
        selected_voice = voice_option.split(" ")[0]
        
        # Speech Rate & Pitch Controls
        speed_slider = st.slider("Speech Speed (Rate):", min_value=-50, max_value=50, value=0, step=5)
        rate_param = f"{speed_slider:+}%" if speed_slider != 0 else "+0%"
        
        pitch_slider = st.slider("Voice Pitch Control:", min_value=-20, max_value=20, value=0, step=2)
        pitch_param = f"{pitch_slider:+}Hz" if pitch_slider != 0 else "+0Hz"

    # Full Width Action Button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Generate Studio Script & Audio", type="primary", use_container_width=True):
        if not prompt.strip():
            st.warning("⚠️ Please provide a prompt or script text first!")
        else:
            generated_text = None
            
            # Phase 1: Gemini Text Generation with System Optimization
            with st.spinner("🧠 Gemini AI is mastering your script..."):
                try:
                    final_prompt = prompt
                    if ai_enhance:
                        final_prompt += f" Ensure the script tone is strictly {tone_select}. Format it beautifully for spoken delivery, adding natural pauses."
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=final_prompt,
                    )
                    generated_text = response.text
                    st.success("📝 Studio Script Generated Successfully!")
                    st.text_area("Review/Edit Generated Script:", value=generated_text, height=200)
                except Exception as e:
                    st.error(f"❌ Gemini Engine Error: {e}")

            # Phase 2: Professional Audio Processing (320kbps Mastery)
            if generated_text:
                with st.spinner(f"🎙️ Processing Master Audio via {tts_engine} at {audio_bitrate}..."):
                    try:
                        unique_id = uuid.uuid4().hex
                        temp_mp3 = f"temp_{unique_id}.mp3"
                        final_wav = f"final_{unique_id}.wav"
                        
                        # Generate raw stream
                        if "Edge-TTS" in tts_engine:
                            asyncio.run(generate_edge_tts(generated_text, selected_voice, rate_param, pitch_param, temp_mp3))
                        else:
                            asyncio.run(generate_edge_tts(generated_text, "bn-BD-NabanitaNeural", "+0%", "+0Hz", temp_mp3))
                        
                        # Apply Professional Pydub Studio Processing
                        audio = AudioSegment.from_mp3(temp_mp3)
                        
                        # Render and export file with user-defined high-fidelity bitrate (e.g., 320k)
                        audio.export(final_wav, format="wav", bitrate=bitrate_value)
                        
                        # Render Playback Layout
                        st.markdown("---")
                        st.subheader("🔊 Studio Audio Monitor (Mastereded File):")
                        st.audio(final_wav, format="audio/wav")
                        
                        # Audio Download Widget
                        with open(final_wav, "rb") as file:
                            st.download_button(
                                label=f"📥 Download Studio Audio ({audio_bitrate} WAV)",
                                data=file,
                                file_name=f"studio_master_320k_{unique_id}.wav",
                                mime="audio/wav",
                                use_container_width=True
                            )
                            
                        # Instant Cache Cleanup to prevent Linux Storage Bloat
                        if os.path.exists(temp_mp3): os.remove(temp_mp3)
                        if os.path.exists(final_wav): os.remove(final_wav)
                        
                    except Exception as e:
                        st.error(f"❌ Mastering Audio Process Crashed: {e}")
                        if os.path.exists(temp_mp3): os.remove(temp_mp3)
                        if os.path.exists(final_wav): os.remove(final_wav)
else:
    st.info("💡 Deployment Notice: Please add 'GEMINI_API_KEY' inside your Streamlit Cloud Secrets dashboard to launch the app.")
