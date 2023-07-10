import librosa
import numpy as np
from middle_column import get_middle_column

# 读取音频文件
audio, sr = librosa.load('audio/20230526180823.wav')

# 计算音频的能量
energy = np.sum(np.abs(audio) ** 2)

# 计算音频的分贝值
db = librosa.power_to_db(energy, ref=np.max)

print("音频文件的分贝值:", db)


# get_middle_column("20230526181130")

get_middle_column("20230526180823")