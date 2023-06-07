import os

# def find_latest_files():
#     filelist = sorted(os.listdir("audio"))
    
#     latest_audio = filelist[-1] if filelist else None
#     latest_text = f"text/{latest_audio.split('.')[0]}.txt" if latest_audio else None
#     latest_audio = f"audio/{latest_audio}" if latest_audio else None

#     print(latest_audio, latest_text)
#     return latest_audio, latest_text

import re
# import chardet
def calculate_speech_rate(text_file):
    file_encoding = "utf8"
    # if not os.path.exists(text_file):
    #     text_file = text_file.replace("text/", "text/done_")
    with open(text_file, 'r', encoding=file_encoding, errors='replace') as file:
        text = file.read()
        # 使用正则表达式匹配中文字符和英文单词，并统计字数
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        english_words = re.findall(r'\b\w+\b', text)
        word_count = len(chinese_chars) + len(english_words)

        # print(text, word_count)
        
    return word_count

import librosa
def calculate_audio_silence(audio_file):
    audio, sr = librosa.load(audio_file, sr=None)
    non_silent_intervals = librosa.effects.split(audio, top_db=12) # 12dB以下的为静音, 12dB以上的为非静音, 这里需要根据实际情况调整
    non_silent_duration = sum([end - start for start, end in non_silent_intervals]) / sr
    audio_duration = len(audio) / sr
    audio_silence = audio_duration - non_silent_duration
    print(audio_duration, sr, non_silent_duration, non_silent_intervals)
    # audio_percent = audio_silence / 60 * 100
    audio_percent = audio_silence / 60
    return audio_percent

# 指定当前文件夹路径
def get_middle_columm(latest_audio):
    # latest_audio, latest_text = find_latest_files()
    latest_text = f"text/{latest_audio}.txt"
    latest_audio = f"audio/{latest_audio}.wav"
    print(latest_audio, latest_text)

    if latest_audio and latest_text:
        speech_rate = calculate_speech_rate(latest_text)
        audio_silence = calculate_audio_silence(latest_audio)

        print("最新的音频文件:", latest_audio)
        print("对应的文本文件:", latest_text)
        print("语速 (字/分钟):", speech_rate)
        print("音频留白率 (%):", audio_silence)
        return speech_rate, audio_silence
    else:
        print("找不到音频文件或文本文件。")
    
        return None, None

# if __name__ == "__main__":
#     get_middle_columm()
