from pydub import AudioSegment
import asrt_sdk
import os
import wave
import math
import base64
import hashlib
import hmac
import json
import os
import time
import requests
import urllib

os.system("docker run --rm -it -p 20001:20001 -p 20002:20002 -d ailemondocker/asrt_service:1.3.0")

# docker run --rm -it -p 20001:20001 -p 20002:20002 --name asrt-server -d ailemondocker/asrt_service:1.3.0
# conda install -c conda-forge asrt-sdk
# docker stop $(docker ps -aq)

def convert_mp3_to_wav(mp3_file_path, wav_file_path):
    # 打开MP3文件
    audio = AudioSegment.from_mp3(mp3_file_path)
    # Resample the audio to 16000 Hz
    resampled_audio = audio.set_frame_rate(16000)
    # 导出为WAV文件
    resampled_audio.export(wav_file_path, format="wav")

def local_convert_mp3_to_text(filepath): # filepath ends with wav

    middle_name = filepath.split('/')[1].split('.')[0]
    os.mkdir(f"{middle_name}")

    FILENAME = f"{filepath.split('.')[0]}.wav"
    text_path = f"text/{middle_name}.txt"
    # convert_mp3_to_wav(filepath, FILENAME)

    HOST = '127.0.0.1'
    PORT = '20001'
    PROTOCOL = 'http'
    SUB_PATH = ''
    speech_recognizer = asrt_sdk.get_speech_recognizer(HOST, PORT, PROTOCOL)
    speech_recognizer.sub_path = SUB_PATH
    segment_length = 512000 // 4

    results_text = []
    with wave.open(FILENAME, 'rb') as wav:
        sample_width = wav.getsampwidth()
        frame_rate = wav.getframerate()
        num_frames = wav.getnframes()

        total_segments = math.ceil(num_frames / segment_length)

        print(f"{sample_width} {frame_rate} {num_frames} {total_segments}")

        for segment_index in range(total_segments):
            segment_start = segment_index * segment_length
            segment_end = min(segment_start + segment_length, num_frames)

            # 读取音频片段
            wav.setpos(segment_start)
            segment_frames = wav.readframes(segment_end - segment_start)
            # 保存音频片段
            with wave.open(f'{middle_name}/{segment_index}.wav', 'wb') as segment_wav:
                segment_wav.setnchannels(wav.getnchannels())
                segment_wav.setsampwidth(sample_width)
                segment_wav.setframerate(frame_rate)
                segment_wav.writeframes(segment_frames)

            wave_data = asrt_sdk.read_wav_datas(f'{middle_name}/{segment_index}.wav')
            result = speech_recognizer.recognite_speech(wave_data.str_data,
                                                        wave_data.sample_rate,
                                                        wave_data.channels,
                                                        wave_data.byte_width)
            # print(result)
            # print(result.result)

            result = speech_recognizer.recognite_language(result.result)
            # print(result)
            print(result.result)
            results_text.append(result.result)

    os.system(f"rm -rf {middle_name}")
    with open(text_path, 'w', encoding='utf8') as f:
        f.writelines(results_text)
    return result.result

def Ifasr(filepath):
    # filepath ends with wav
    middle_name = filepath.split('/')[1].split('.')[0]
    FILENAME = f"{filepath.split('.')[0]}.wav"
    text_path = f"text/{middle_name}.txt"
    # convert_mp3_to_wav(filepath, FILENAME)

    lfasr_host = 'https://raasr.xfyun.cn/v2/api'
    # 请求的接口名
    api_upload = '/upload'
    api_get_result = '/getResult'

    class RequestApi(object):
        def __init__(self, appid, secret_key, upload_file_path):
            self.appid = appid
            self.secret_key = secret_key
            self.upload_file_path = upload_file_path
            self.ts = str(int(time.time()))
            self.signa = self.get_signa()

        def get_signa(self):
            appid = self.appid
            secret_key = self.secret_key
            m2 = hashlib.md5()
            m2.update((appid + self.ts).encode('utf-8'))
            md5 = m2.hexdigest()
            md5 = bytes(md5, encoding='utf-8')
            # 以secret_key为key, 上面的md5为msg， 使用hashlib.sha1加密结果为signa
            signa = hmac.new(secret_key.encode('utf-8'), md5, hashlib.sha1).digest()
            signa = base64.b64encode(signa)
            signa = str(signa, 'utf-8')
            return signa

        def upload(self):
            print("上传部分：")
            upload_file_path = self.upload_file_path
            file_len = os.path.getsize(upload_file_path)
            file_name = os.path.basename(upload_file_path)

            param_dict = {}
            param_dict['appId'] = self.appid
            param_dict['signa'] = self.signa
            param_dict['ts'] = self.ts
            param_dict["fileSize"] = file_len
            param_dict["fileName"] = file_name
            param_dict["duration"] = "200"
            param_dict["eng_colloqproc"] = True # 开启口语规整
            print("upload参数：", param_dict)
            data = open(upload_file_path, 'rb').read(file_len)

            response = requests.post(url =lfasr_host + api_upload+"?"+urllib.parse.urlencode(param_dict),
                                    headers = {"Content-type":"application/json"},data=data)
            print("upload_url:",response.request.url)
            result = json.loads(response.text)
            print("upload resp:", result)
            return result
        
        def post_process(self, result): # dict -> list [str, str, ...]

            order_result = result['content']['orderResult']
            order_result_json = json.loads(order_result) # 解析orderResult字段内容为JSON对象
            # 获取lattice字段的值
            lattice = order_result_json['lattice'] #lattice2

            # 解析lattice中的json_1best字段内容
            words = []
            for item in lattice:
                json_1best = item['json_1best']
                json_1best_json = json.loads(json_1best)
                rt = json_1best_json['st']['rt']
                
                # 提取文字和标点符号
                transcription = ""
                for rt_item in rt:
                    ws = rt_item['ws']
                    for ws_item in ws:
                        cw = ws_item['cw']
                        for cw_item in cw:
                            w = cw_item['w']
                            transcription += w

                # 输出转写结果
                print("转写结果：", transcription)
                words.append(transcription)
            return words


        def get_result(self):
            uploadresp = self.upload()
            orderId = uploadresp['content']['orderId']
            param_dict = {}
            param_dict['appId'] = self.appid
            param_dict['signa'] = self.signa
            param_dict['ts'] = self.ts
            param_dict['orderId'] = orderId
            param_dict['resultType'] = "transfer,predict"


            print("")
            print("查询部分：")
            print("get result参数：", param_dict)
            status = 3
            # 建议使用回调的方式查询结果，查询接口有请求频率限制
            while status == 3:
                response = requests.post(url=lfasr_host + api_get_result + "?" + urllib.parse.urlencode(param_dict),
                                        headers={"Content-type": "application/json"})
                # print("get_result_url:",response.request.url)
                result = json.loads(response.text)
                print(result)
                status = result['content']['orderInfo']['status']
                print("status=",status)
                if status == 4:
                    break
                time.sleep(5)
            print("get_result resp:",result)

            result = self.post_process(result)

            return result

    api = RequestApi(appid="4ff90583",
                     secret_key="7fe3104bb47b1400afb13811758dc3b6",
                     upload_file_path=FILENAME)

    result = api.get_result()
    with open(text_path, 'w', encoding='utf8') as f:
        f.writelines(result)
    return result

def convert_mp3_to_text(filepath, mode="ifasr"): # filepath ends with wav
    if mode == "ifasr":    
        Ifasr(filepath)
    elif mode == "local":
        local_convert_mp3_to_text(filepath)

if __name__ == "__main__":
    convert_mp3_to_text("audio/20230521132639.wav")