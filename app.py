import warnings
import sys

# Suppress all unwanted background warnings from third-party libraries
if not sys.warnoptions:
    warnings.simplefilter("ignore", category=SyntaxWarning)
    warnings.simplefilter("ignore", category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)

import streamlit as st
from google import genai  # Upgraded to modern 2026 google-genai library
import asyncio
import edge_tts
import os
import re
import random
import tempfile
import uuid
import time
from pydub import AudioSegment
from pydub import effects 

# Page Configuration
st.set_page_config(
    page_title="Multi-Lang Studio TTS Pro",
    page_icon="🎙️",
    layout="wide"
)

# Premium Animated & Modern UI Styling (CSS Injection)
st.markdown("""
    <style>
    .main-title {
        font-size: 2.8rem !important;
        font-weight: 800 !important;
        background: linear-gradient(45deg, #FF4B4B, #4A90E2, #1DD1A1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.2rem;
        animation: fadeIn 1.5s ease-in-out;
    }
    .sub-title {
        text-align: center;
        color: #A0AEC0;
        font-size: 1.1rem;
        margin-bottom: 1.8rem;
    }
    @keyframes fadeIn {
        0% { opacity: 0; transform: translateY(-10px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.01); }
        100% { transform: scale(1); }
    }
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #6C5CE7, #A8DA6C) !important;
        color: white !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 2rem !important;
        transition: all 0.3s ease-in-out !important;
        box-shadow: 0 4px 15px rgba(108, 92, 231, 0.3) !important;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(108, 92, 231, 0.5) !important;
        animation: pulse 1s infinite;
    }
    </style>
""", unsafe_allow_html=True)

# Render Styled Header
st.markdown('<h1 class="main-title">🎙️ Multi-Lang Studio TTS Pro</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Advanced Podcast & Audiobook Production Engine with AI Studio Mastering</p>', unsafe_allow_html=True)

# WINDOWS ASYNCIO BUG PATCH
if sys.platform == 'win32':
    from asyncio.proactor_events import _ProactorBasePipeTransport
    
    def silence_proactor_bug(self, exc):
        if isinstance(exc, ConnectionResetError) or (exc and "10054" in str(exc)):
            return
        return original_call_connection_lost(self, exc)
        
    if hasattr(_ProactorBasePipeTransport, '_call_connection_lost'):
        original_call_connection_lost = _ProactorBasePipeTransport._call_connection_lost
        _ProactorBasePipeTransport._call_connection_lost = silence_proactor_bug

# Initialize Request Counters in Session State
if "requests_2_5_flash" not in st.session_state:
    st.session_state.requests_2_5_flash = 0
if "requests_2_0_flash" not in st.session_state:
    st.session_state.requests_2_0_flash = 0

# Secure API Key Fetching & Gemini Initialization
def _get_secret(key):
    try: return st.secrets.get(key)
    except Exception: return None

GEMINI_API_KEY = (
    os.environ.get("GEMINI_API_KEY")
    or _get_secret("GEMINI_API_KEY")
    or "AQ.Ab8RN6ISbcNHh4lnQcF7ksvYmmV628mtiVJOUuT0UyzDxDeh0w"
)

@st.cache_resource
def get_gemini_client(api_key):
    try: return genai.Client(api_key=api_key)
    except Exception: return None

client = get_gemini_client(GEMINI_API_KEY)

# Sidebar Configuration Panel
st.sidebar.header("🌐 Global Settings")

# Language Selection
lang_option = st.sidebar.selectbox(
    "Select Language:",
    ["Bangla (Bengali)", "English (US/UK)"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Audio Processing Engine")
engine_option = st.sidebar.selectbox(
    "Select Engine Mode:",
    [
        "Gemini 2.5 Flash (AI Script Optimize)", 
        "Gemini 2.0 Flash (AI Script Optimize)", 
        "Direct Microsoft TTS (100% Free & Unlimited)"
    ]
)

# AI Quota & Limits Display Logic
remaining_req = 99999  
current_model_id = "Microsoft Neural Engine"

if "2.5 Flash" in engine_option:
    current_model_id = "gemini-2.5-flash"
    used_req = st.session_state.requests_2_5_flash
    remaining_req = max(0, 20 - used_req)
    st.sidebar.info(f"📊 **AI Quota Status ({current_model_id}):**\n* Sent Requests: **{used_req}**\n* Today's Free Limit Left: **{remaining_req}/20**")
elif "2.0 Flash" in engine_option:
    current_model_id = "gemini-2.0-flash"
    used_req = st.session_state.requests_2_0_flash
    remaining_req = max(0, 20 - used_req)
    st.sidebar.info(f"📊 **AI Quota Status ({current_model_id}):**\n* Sent Requests: **{used_req}**\n* Today's Free Limit Left: **{remaining_req}/20**")
else:
    st.sidebar.success("🟢 **Microsoft TTS Mode Active:**\nNo AI limits or request quotas in this mode.")

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Voice Customization")

if lang_option == "Bangla (Bengali)":
    voice_option = st.sidebar.selectbox(
        "Voice Model (BN Voices):",
        ["bn-BD-PradeepNeural (Male - Deep)", "bn-BD-NabanitaNeural (Female - Fluent)"]
    )
    selected_voice = "bn-BD-PradeepNeural" if "Pradeep" in voice_option else "bn-BD-NabanitaNeural"
    default_speed, default_pitch = -8, -3
else:
    voice_option = st.sidebar.selectbox(
        "Voice Model (EN Voices):",
        [
            "en-US-AndrewNeural (Male - News/Podcast)", 
            "en-US-EmmaNeural (Female - Audiobook)",
            "en-GB-RyanNeural (Male - British Deep)",
            "en-US-BrianNeural (Male - Crisp)"
        ]
    )
    selected_voice = voice_option.split(" ")[0]
    default_speed, default_pitch = 0, 0

speed_slider = st.sidebar.slider("Base Speed:", min_value=-50, max_value=50, value=default_speed, step=2)
pitch_slider = st.sidebar.slider("Base Pitch:", min_value=-20, max_value=20, value=default_pitch, step=1)

st.sidebar.markdown("---")
st.sidebar.subheader("⏱️ Custom Pause Control")

if lang_option == "Bangla (Bengali)":
    p1_label, p1_char = "Pause after Dandi (।) (ms):", "।"
    p2_label, p2_char = "Pause after Comma (,) (ms):", ","
else:
    p1_label, p1_char = "Pause after Full Stop (.) (ms):", "."
    p2_label, p2_char = "Pause after Comma (,) (ms):", ","

pause_p1 = st.sidebar.slider(p1_label, min_value=0, max_value=1200, value=300, step=50)
pause_p2 = st.sidebar.slider(p2_label, min_value=0, max_value=600, value=120, step=20)
pause_excl = st.sidebar.slider("Pause after Exclamation (!) (ms):", min_value=0, max_value=1000, value=250, step=50)
pause_ques = st.sidebar.slider("Pause after Question (?) (ms):", min_value=0, max_value=1000, value=250, step=50)

pause_settings = {
    p1_char: pause_p1,
    p2_char: pause_p2,
    '!': pause_excl,
    '?': pause_ques,
    ';': pause_p2,
    '\n': pause_p1
}

st.sidebar.markdown("---")
st.sidebar.subheader("🌬️ Advanced Studio Mixer")
naturalness_level = st.sidebar.slider("Naturalness Intensity (Jitter):", min_value=0, max_value=10, value=6)
crossfade_ms = st.sidebar.slider("Crossfade Blending (ms):", min_value=0, max_value=300, value=120)

# Main Studio Controls
col_ui1, col_ui2 = st.columns([1, 1], gap="medium")

with col_ui1:
    st.markdown("### 🎚️ Voice Mastering Control")
    enable_enhancer = st.checkbox(
        "Activate AI Voice Enhancer (High-Pass Filter, Compressor & Normalizer)", 
        value=True, 
        help="When enabled, this removes low-frequency hums (e.g., fan/AC noise), balances voice levels, and boosts overall loudness."
    )

with col_ui2:
    st.markdown("### 💽 High-Fidelity Master")
    audio_bitrate = st.selectbox(
        "Mastering Quality Target Bitrate:",
        ["320 kbps (Studio Master / HD)", "256 kbps (High Quality)", "128 kbps (Standard MP3)"]
    )
    bitrate_value = audio_bitrate.split(" ")[0] + "k"

st.markdown("---")

# Main Script Input Area
st.subheader("📝 Paste Your Script or Text Below")
text_input = st.text_area(
    label="Script Input Field",
    height=220,
    placeholder="Type or paste your script here (Bangla or English)...",
    label_visibility="collapsed"
)

# --- Core Audio Processing Functions (Fully Retained from Your Script) ---
def segment_text(text, lang):
    text = re.sub(r'[\s]+', ' ', text)
    text = re.sub(r'[\*\_\`\-\"#]', '', text)
    punctuation_pattern = r'([।,!?;\n])' if lang == "Bangla (Bengali)" else r'([.,!?;\n])'
    parts = re.split(punctuation_pattern, text)
    segments = []
    buf = ""
    active_puncts = ['।', ',', '!', '?', ';', '\n'] if lang == "Bangla (Bengali)" else ['.', ',', '!', '?', ';', '\n']
    
    for part in parts:
        if part in active_puncts:
            buf += part
            if buf.strip():
                segments.append(buf.strip())
            buf = ""
        else:
            buf += part
    if buf.strip():
        segments.append(buf.strip())
    return [s for s in segments if s]

def get_segment_end_punct(segment, lang):
    fallback = '।' if lang == "Bangla (Bengali)" else '.'
    active_puncts = ['।', ',', '!', '?', ';'] if lang == "Bangla (Bengali)" else ['.', ',', '!', '?', ';']
    if segment and segment[-1] in active_puncts:
        return segment[-1]
    return fallback

def clean_segment_for_tts(text, lang):
    pattern = r'[।,!?;\s]+$' if lang == "Bangla (Bengali)" else r'[.,!?;\s]+$'
    return re.sub(pattern, '', text)

def jittered_prosody_and_volume(base_speed, base_pitch, punct, intensity):
    if intensity <= 0:
        return f"{base_speed:+}%", f"{base_pitch:+}Hz", 0.0
    scale = intensity / 10.0
    speed_jitter = random.randint(-int(5 * scale), int(5 * scale))
    pitch_jitter = random.randint(-int(3 * scale), int(3 * scale))
    volume_db = random.uniform(-1.0 * scale, 1.0 * scale)
    if punct in ['!', '?']:
        pitch_jitter += int(3 * scale)
        volume_db += (1.0 * scale)
    elif punct == ',':
        speed_jitter -= int(2 * scale)
    final_speed = max(-50, min(50, base_speed + speed_jitter))
    final_pitch = max(-20, min(20, base_pitch + pitch_jitter))
    return f"{final_speed:+}%", f"{final_pitch:+}Hz", volume_db

def pause_duration_for_punct(punct, pause_map, intensity):
    base = pause_map.get(punct, 200)
    if intensity <= 0 or base <= 50:
        return base
    jitter_range = int(base * 0.15 * (intensity / 10.0))
    return max(0, base + random.randint(-jitter_range, jitter_range))

async def synthesize_segment(text, voice, rate, pitch, out_path):
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(out_path)

def _load_mp3_with_retry(path, retries=5, delay=0.2):
    for attempt in range(retries):
        try: return AudioSegment.from_mp3(path)
        except (PermissionError, OSError): time.sleep(delay)
    return AudioSegment.silent(duration=100)

async def generate_multilang_tts(segments, voice, base_speed, base_pitch, pause_map, intensity, xfade, lang, target_bitrate, progress_callback=None):
    final_audio = AudioSegment.silent(duration=0)
    temp_files = []
    temp_dir = tempfile.mkdtemp(prefix="studio_tts_")
    try:
        for i, segment in enumerate(segments):
            punct = get_segment_end_punct(segment, lang)
            rate, pitch, volume_db = jittered_prosody_and_volume(base_speed, base_pitch, punct, intensity)
            clean_text = clean_segment_for_tts(segment, lang)
            if not clean_text.strip(): clean_text = segment

            temp_path = os.path.join(temp_dir, f"_seg_{i}_{uuid.uuid4().hex}.mp3")
            temp_files.append(temp_path)
            await synthesize_segment(clean_text, voice, rate, pitch, temp_path)
            clip = _load_mp3_with_retry(temp_path) + volume_db

            if len(final_audio) == 0: final_audio = clip
            else:
                if xfade > 0 and len(final_audio) > xfade and len(clip) > xfade:
                    final_audio = final_audio.append(clip, crossfade=xfade)
                else: final_audio += clip
            if i < len(segments) - 1:
                gap = pause_duration_for_punct(punct, pause_map, intensity)
                if gap > 0: final_audio += AudioSegment.silent(duration=gap)
            if progress_callback: progress_callback((i + 1) / len(segments))

        output_path = os.path.join(tempfile.gettempdir(), f"final_studio_output_{uuid.uuid4().hex}.mp3")
        final_audio.export(output_path, format="mp3", bitrate=target_bitrate, parameters=["-ar", "44100", "-q", "0"])
        return output_path
    finally:
        for f in temp_files:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass
        try: os.rmdir(temp_dir)
        except: pass

# Generate Button Action
if st.button("🚀 Generate Studio-Quality Audio", type="primary", use_container_width=True):
    if not text_input.strip():
        st.error("❌ Please input some text/script to process!")
    elif "Direct Microsoft" not in engine_option and remaining_req <= 0:
        st.error(f"🚨 Free daily quota reached for {current_model_id}! Please switch to 'Direct Microsoft TTS' mode.")
    else:
        try:
            if "Direct Microsoft" not in engine_option:
                if current_model_id == "gemini-2.5-flash":
                    st.session_state.requests_2_5_flash += 1
                else:
                    st.session_state.requests_2_0_flash += 1

            optimized_text = text_input.strip()

            if "Direct Microsoft" not in engine_option:
                if not client:
                    st.error("❌ Google GenAI client configuration error. Check your API Key setup.")
                else:
                    with st.spinner(f"🤖 {current_model_id} is optimizing your script..."):
                        if lang_option == "Bangla (Bengali)":
                            prompt = f"Optimize this Bengali voice-over script. Fix grammar and add proper punctuation (।, ?, !, ,) at natural breathing points. Output ONLY the raw optimized text:\n\n{text_input}"
                        else:
                            prompt = f"Optimize this English podcast/audiobook script. Make it flow naturally for verbal narration. Fix grammar and add clear punctuation (. , ! ? —). Output ONLY the raw optimized text:\n\n{text_input}"

                        # Modern google-genai 2026 syntax mapping
                        response = client.models.generate_content(
                            model=current_model_id,
                            contents=prompt,
                        )
                        optimized_text = response.text.strip()
            else:
                with st.spinner("⚡ Microsoft TTS is directly processing the script..."):
                    time.sleep(0.5)

            # Audio Rendering Framework
            with st.spinner(f"🎙️ Rendering audio on a {audio_bitrate} HD master line..."):
                segments = segment_text(optimized_text, lang_option)
                progress_bar = st.progress(0.0, text="Generating Voice...")

                def update_progress(frac):
                    progress_bar.progress(frac, text=f"Generating Voice... ({int(frac*100)}%)")

                try: 
                    if sys.platform == 'win32':
                        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                final_audio_path = loop.run_until_complete(
                    generate_multilang_tts(
                        segments, selected_voice, speed_slider, pitch_slider,
                        pause_settings, naturalness_level, crossfade_ms, lang_option,
                        bitrate_value, update_progress
                    )
                )
                progress_bar.empty()

            # AI Voice Enhancer Processing
            if os.path.exists(final_audio_path):
                voice_audio = AudioSegment.from_mp3(final_audio_path)

                if enable_enhancer:
                    with st.spinner("✨ Mastering audio with AI Voice Enhancer..."):
                        voice_audio = voice_audio.high_pass_filter(80)
                        voice_audio = effects.compress_dynamic_range(voice_audio, threshold=-16.0, ratio=3.0)
                        voice_audio = effects.normalize(voice_audio)
                
                # Dynamic Bitrate Output Handling (320k / 256k / 128k)
                voice_audio.export(final_audio_path, format="mp3", bitrate=bitrate_value)

                with open(final_audio_path, "rb") as file:
                    audio_bytes = file.read()

                st.success("🎉 Your studio-quality enhanced audio file is ready!")

                if "Direct Microsoft" not in engine_option:
                    with st.expander("👁️ View Optimized Final Script Generated by Gemini AI"):
                        st.write(optimized_text)

                st.audio(audio_bytes, format="audio/mp3")
                st.download_button(
                    label=f"⬇️ Download Mastered Audio File ({audio_bitrate})",
                    data=audio_bytes,
                    file_name=f"studio_enhanced_master_{bitrate_value}.mp3",
                    mime="audio/mp3",
                    use_container_width=True
                )

                try: os.remove(final_audio_path)
                except: pass

        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                st.error("⚠️ Google API Free Quota Limit Exceeded! Please select 'Direct Microsoft TTS' mode.")
            else:
                st.error(f"🚨 A system error occurred: {str(e)}")
