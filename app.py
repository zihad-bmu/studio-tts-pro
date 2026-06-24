import streamlit as st
import google.generativeai as genai
import asyncio
import edge_tts
import os
import re
import random
import tempfile
import uuid
import time
import sys
from pydub import AudioSegment
from pydub import effects 

# Page Configuration
st.set_page_config(
    page_title="Multi-Lang Studio TTS Pro",
    page_icon="🎙️",
    layout="wide"
)

# WINDOWS ASYNCIO BUG PATCH: Silences the ProactorEventLoop connection lost warning on Windows
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

st.title("🎙️ Studio-Quality Multi-Language Voice Generator")
st.subheader("Bengali & English Podcast & Audiobook Production Engine (with Advanced AI Voice Enhancer)")
st.markdown("---")

def _get_secret(key):
    try:
        return st.secrets.get(key)
    except Exception:
        return None

GEMINI_API_KEY = (
    os.environ.get("GEMINI_API_KEY")
    or _get_secret("GEMINI_API_KEY")
    or "AQ.Ab8RN6ISbcNHh4lnQcF7ksvYmmV628mtiVJOUuT0UyzDxDeh0w"
)
genai.configure(api_key=GEMINI_API_KEY)

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

# Studio Enhancer Control Panel
st.markdown("### 🎚️ Voice Mastering Control")
enable_enhancer = st.checkbox(
    "Activate AI Voice Enhancer (High-Pass Filter, Compressor & Normalizer)", 
    value=True, 
    help="When enabled, this removes low-frequency hums (e.g., fan/AC noise), balances voice levels, and boosts overall loudness."
)
st.markdown("---")

# Main Script Input Area
st.subheader("📝 Paste Your Script or Text Below")
text_input = st.text_area(
    label="Script Input Field",
    height=250,
    placeholder="Type or paste your script here (Bangla or English)...",
    label_visibility="collapsed"
)

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

async def generate_multilang_tts(segments, voice, base_speed, base_pitch, pause_map, intensity, xfade, lang, progress_callback=None):
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
        final_audio.export(output_path, format="mp3", bitrate="320k", parameters=["-ar", "44100", "-q", "0"])
        return output_path
    finally:
        for f in temp_files:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass
        try: os.rmdir(temp_dir)
        except: pass

# Generate Button Action
if st.button("🚀 Generate Studio-Quality Audio", type="primary"):
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
                with st.spinner(f"🤖 {current_model_id} is optimizing your script..."):
                    model = genai.GenerativeModel(current_model_id)

                    if lang_option == "Bangla (Bengali)":
                        prompt = f"Optimize this Bengali voice-over script. Fix grammar and add proper punctuation (।, ?, !, ,) at natural breathing points. Output ONLY the raw optimized text:\n\n{text_input}"
                    else:
                        prompt = f"Optimize this English podcast/audiobook script. Make it flow naturally for verbal narration. Fix grammar and add clear punctuation (. , ! ? —). Output ONLY the raw optimized text:\n\n{text_input}"

                    response = model.generate_content(prompt, generation_config={"response_mime_type": "text/plain"})
                    optimized_text = response.text.strip()
            else:
                with st.spinner("⚡ Microsoft TTS is directly processing the script..."):
                    time.sleep(0.5)

            # Audio Rendering Framework
            with st.spinner("🎙️ Rendering audio on a 320kbps HD master line..."):
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
                        update_progress
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
                
                voice_audio.export(final_audio_path, format="mp3", bitrate="320k")

                with open(final_audio_path, "rb") as file:
                    audio_bytes = file.read()

                st.success("🎉 Your studio-quality enhanced audio file is ready!")

                if "Direct Microsoft" not in engine_option:
                    with st.expander("👁️ View Optimized Final Script Generated by Gemini AI"):
                        st.write(optimized_text)

                st.audio(audio_bytes, format="audio/mp3")
                st.download_button(
                    label="⬇️ Download Mastered Audio File (320kbps MP3)",
                    data=audio_bytes,
                    file_name="studio_enhanced_voice.mp3",
                    mime="audio/mp3"
                )

                try: os.remove(final_audio_path)
                except: pass

        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                st.error("⚠️ Google API Free Quota Limit Exceeded! Please select 'Direct Microsoft TTS' mode.")
            else:
                st.error(f"🚨 A system error occurred: {str(e)}")