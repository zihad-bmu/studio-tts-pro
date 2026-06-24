import streamlit as st
from google import genai
import asyncio
from edge_tts import Communicate
from pydub import AudioSegment
import uuid
import os

# ১. পেজ কনফিগারেশন এবং স্টাইলিং
st.set_page_config(
    page_title="Studio TTS Pro",
    page_icon="🎙️",
    layout="centered"
)

st.title("🎙️ Studio TTS Pro")
st.write("Gemini AI দিয়ে টেক্সট জেনারেট করুন এবং Edge-TTS দিয়ে প্রিমিয়াম অডিওতে কনভার্ট করুন।")

# ২. জেমিনি এআই ক্লায়েন্ট সেটআপ (নতুন google-genai লাইব্রেরি অনুসারে)
@st.cache_resource
def get_gemini_client():
    try:
        # Streamlit Secrets থেকে API Key রিড করা হচ্ছে
        api_key = st.secrets["GEMINI_API_KEY"]
        return genai.Client(api_key=api_key)
    except KeyError:
        st.error("❌ Streamlit Secrets-এ 'GEMINI_API_KEY' খুঁজে পাওয়া যায়নি! দয়া করে Secrets চেক করুন।")
        return None
    except Exception as e:
        st.error(f"❌ Gemini Client সেটআপে সমস্যা: {e}")
        return None

client = get_gemini_client()

# ৩. এজ টিটিএস (Edge-TTS) ফাংশন (Async-হ্যান্ডলিং সহ)
async def generate_edge_tts(text, voice, output_path):
    communicate = Communicate(text, voice)
    await communicate.save(output_path)

# ৪. মেইন অ্যাপ্লিকেশন লজিক
if client:
    # ইনপুট সেকশন
    prompt = st.text_area("আপনার প্রম্পট লিখুন (এখানে যা লিখবেন, জেমিনি তার ওপর ভিত্তি করে স্ক্রিপ্ট তৈরি করবে):", 
                          placeholder="যেমন: একটি সুন্দর মোটিভেশনাল স্ক্রিপ্ট লিখে দাও...")
    
    # ভয়েস সিলেকশন (Edge TTS এর কিছু জনপ্রিয় বাংলা ও ইংরেজি ভয়েস)
    voice_option = st.selectbox(
        "ভয়েস সিলেক্ট করুন:",
        [
            "bn-BD-PradeepNeural (বাংলা - পুরুষ)",
            "bn-BD-NabanitaNeural (বাংলা - নারী)",
            "en-US-AriaNeural (English - Female)",
            "en-US-GuyNeural (English - Male)"
        ]
    )
    
    # ভয়েস স্ট্রিং ফরম্যাটিং
    selected_voice = voice_option.split(" ")[0]

    if st.button("Generate Script & Audio", type="primary"):
        if not prompt.strip():
            st.warning("⚠️ দয়া করে আগে কিছু লিখুন!")
        else:
            with st.spinner("🧠 Gemini AI স্ক্রিপ্ট তৈরি করছে..."):
                try:
                    # ২০২৬ সালের লেটেস্ট ও স্টেবল মডেল 'gemini-2.5-flash' ব্যবহার করা হয়েছে
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                    )
                    generated_text = response.text
                    
                    st.success("📝 স্ক্রিপ্ট জেনারেশন সফল হয়েছে!")
                    st.subheader("📄 জেনারেটেড স্ক্রিপ্ট:")
                    st.write(generated_text)
                    
                except Exception as e:
                    st.error(f"❌ জেমিনি সার্ভার থেকে রেসপন্স পেতে সমস্যা হয়েছে: {e}")
                    generated_text = None

            # অডিও জেনারেশন পার্ট
            if generated_text:
                with st.spinner("🎙️ স্ক্রিপ্ট থেকে অডিও তৈরি হচ্ছে..."):
                    try:
                        # ইউনিক ফাইল নেম তৈরি
                        unique_id = uuid.uuid4().hex
                        temp_mp3 = f"temp_{unique_id}.mp3"
                        final_wav = f"final_{unique_id}.wav"
                        
                        # Edge-TTS রান করা (Async টু Sync ব্রিজ)
                        asyncio.run(generate_edge_tts(generated_text, selected_voice, temp_mp3))
                        
                        # Pydub এবং FFmpeg দিয়ে অডিও প্রসেসিং টেস্ট (যদি কোনো এফেক্ট দিতে চান)
                        audio = AudioSegment.from_mp3(temp_mp3)
                        
                        # এখানে ফাইলটি .wav বা .mp3 হিসেবে সেভ করতে পারেন
                        audio.export(final_wav, format="wav")
                        
                        # স্ট্রিমলিট প্লেয়ারে অডিও দেখানো
                        st.subheader("🔊 আপনার তৈরি অডিও:")
                        st.audio(final_wav, format="audio/wav")
                        
                        # ডাউনলোড বাটন
                        with open(final_wav, "rb") as file:
                            st.download_button(
                                label="📥 ডাউনলোড অ디오 (WAV)",
                                data=file,
                                file_name=f"studio_tts_{unique_id}.wav",
                                mime="audio/wav"
                            )
                            
                        # অস্থায়ী ফাইলগুলো মুছে ফেলা (সার্ভারের স্টোরেজ ক্লিন রাখার জন্য)
                        if os.path.exists(temp_mp3): os.remove(temp_mp3)
                        if os.path.exists(final_wav): os.remove(final_wav)
                        
                    except Exception as e:
                        st.error(f"❌ অ디오 প্রসেস করতে সমস্যা হয়েছে। [Internal Error: {e}]")
                        # ক্র্যাশ করলেও ব্যাকআপ ফাইল রিমুভ করার চেষ্টা
                        if os.path.exists(temp_mp3): os.remove(temp_mp3)
else:
    st.info("💡 অ্যাপটি চালু করতে প্রথমে আপনার Streamlit Cloud Secrets-এ 'GEMINI_API_KEY' যোগ করুন।")
