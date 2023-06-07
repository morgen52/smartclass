from flask import Flask, request, jsonify, current_app
import os
import json
from flask_cors import CORS
import sqlite3
import datetime
import time
from myclear import clear
import threading
import multiprocessing
import random

app = Flask(__name__)
origins = [
    'http://localhost',
    'http://127.0.0.1',
    'http://162.105.175.69'
]
CORS(app, origins=origins)

app.lock = 0 # 0: 未锁定 1: 锁定。科大讯飞只能同时有一个请求

def init():

    # clear()
    # conn = sqlite3.connect('database.db')
    # # 数据库中包含{"teacher_score": 0.31818479890402707, "student_score": 0.5, "latest_audio": "20230525213529", "speed": 0, "audio_silence": 0.0, "student_score_history": [0.5, 0.5], "teacher_score_history": [0.25112356228156835, 0.2523034238621179, 0.25327794621317945]}
    # # teacher_score: 老师的评分
    # # student_score: 学生的评分
    # # latest_audio: 最新的音频文件名
    # # speed: 语速
    # # audio_silence: 音频静音时间
    # # student_score_history: 学生的评分历史
    # # teacher_score_history: 老师的评分历史
    # # 以上数据在数据库中的表名为"cur_state"
    # cursor = conn.cursor()
    # # 先清空表
    # cursor.execute('''
    #     DROP TABLE IF EXISTS cur_state
    # ''')
    # conn.commit()
    # # 创建cur_state表
    # cursor.execute('''
    #     CREATE TABLE IF NOT EXISTS cur_state (
    #         teacher_score REAL,
    #         student_score REAL,
    #         latest_audio TEXT,
    #         latest_pic TEXT,
    #         speed INTEGER,
    #         audio_silence REAL,
    #         student_score_history TEXT,
    #         teacher_score_history TEXT,
    #         summary TEXT,
    #         raw_text TEXT
    #     )
    # ''')
    # # 插入初始数据
    # cursor.execute('''
    #     INSERT INTO cur_state VALUES (0.0, 0.0, '', '', 0, 0.0, '[]', '[]', '', '')
    # ''')
    # conn.commit()
    # conn.close()

    os.system("docker stop $(docker ps -a -q)")

    os.system("docker run --rm -p 5000:5000 -d liminfinity/smartclass/text:0.0 python3 flask_server.py")
    os.system("docker run -v $(pwd)/audio:/app/audio --rm -p 5001:5001 -d liminfinity/smartclass/audio:0.0 python3 flask_server.py")
    os.system("docker run -v $(pwd)/pic:/app/pic --rm -p 5002:5002 -d liminfinity/smartclass/video:0.0 python3 flask_server.py")

init()
from middle_columm import get_middle_columm
from audio2text import convert_mp3_to_text

def print_database():
    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    cursor.execute("SELECT * FROM cur_state")
    row = cursor.fetchone()
    # timestamp = time.strftime("%Y%m%d%H%M%S", time.localtime())
    try:
        with open(f"log/log.txt", 'w', encoding='utf8') as f:
            while row:
                f.write(str(row) + '\n')
                row = cursor.fetchone()
    except Exception as e:
        print("print_database error", e)
    db.close()

def gen_middle_columm(cur_latest_audio):
    # if not cur_latest_audio:
    #     filelist = sorted(os.listdir("audio"))
    #     cur_latest_audio = filelist[-1].split('.')[0] if filelist else None # audio 没有done标记

    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    cursor.execute("SELECT latest_audio FROM cur_state")
    result = cursor.fetchone()
    db.close()
    if result and result[0] == cur_latest_audio:
        return

    speech_rate, audio_silence = get_middle_columm(cur_latest_audio)
    data = {
        "speech_rate": speech_rate,
        "audio_silence": audio_silence
    }

    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    cursor.execute("UPDATE cur_state SET speed = ?, audio_silence = ?", (speech_rate, audio_silence))
    db.commit()
    db.close()
    return 

def compute_score(pos, neu, neg):
    all = 2 * (pos + neu + neg)
    if all:
        score = (pos * 2 + neu * 1) / all
        return score
    else:
        return 0.5 + random.uniform(-0.05, 0.05)

def gen_teacher_emotion(latest_file):
    # 获取timestamp最近的文件
    # latest_file = sorted(os.listdir("audio"))[-1].split('.')[0]

    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    cursor.execute("SELECT latest_audio FROM cur_state")
    result = cursor.fetchone()
    db.close()
    if result and result[0] == latest_file: # 如果数据库中的latest_audio和文件夹中的一致
        print(f"{latest_file} has been processed, no need to update")
        return # 不需要更新
    
    new_files = []
    for filename in sorted(os.listdir("audio")):
        # print(filename)
        if result[0] < filename.split('.')[0] <= latest_file:
            new_files.append(filename.split('.')[0])

    print("teacher emotion audio and text new_files", new_files)
    texts = []
    text_emotion = {
        "pos_num": 0, 
        "neu_num": 0,
        "neg_num": 0
    }
    for filename in new_files:
        with open(f"text/{filename}.txt", 'r', encoding='utf8') as f:
            texts.append(f.read())
    
    for text in texts:
        data = {
            "text": text
        }
        emotion_resp = requests.post(f"http://localhost:5000/text", json=data)
        emotion_resp = emotion_resp.json()
        print(emotion_resp)
        text_emotion['pos_num'] += emotion_resp['pos_num']
        text_emotion['neu_num'] += emotion_resp['neu_num']
        text_emotion['neg_num'] += emotion_resp['neg_num']

    text_score = compute_score(text_emotion['pos_num'], text_emotion['neu_num'], text_emotion['neg_num'])
        
    # update raw_text
    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    # 先获得数据库中的raw_text
    cursor.execute("SELECT raw_text FROM cur_state")
    result = cursor.fetchone()
    if result:
        raw_text = result[0]
    else:
        raw_text = ""
    # 更新raw_text
    raw_text += '。'.join(texts)
    cursor.execute("UPDATE cur_state SET raw_text = ?", (raw_text,))
    db.commit()
    db.close()

    # {"pos_num": 2, "neg_num": 0, "neu_num": 4}

    audio_emotion = {
        "pos_num": 0, 
        "neu_num": 0,
        "neg_num": 0
    }
    for filename in new_files:
        audiopath = f"audio/{filename}.wav"
        data = {
            "path": audiopath
        }
        response = requests.post("http://localhost:5001/audio", json=data)
        response = response.json()
        print(response)
        # {'angry': 0,'fear': 0,'happy': 0,'neutral': 0,'sad': 0,'surprise': 0}
        pos_cnt = response['happy'] + response['surprise']
        neg_cnt = response['angry'] + response['fear'] + response['sad']
        neu_cnt = response['neutral']
        audio_emotion['pos_num'] += pos_cnt
        audio_emotion['neu_num'] += neu_cnt
        audio_emotion['neg_num'] += neg_cnt

    audio_score = compute_score(audio_emotion['pos_num'], audio_emotion['neu_num'], audio_emotion['neg_num'])

    teacher_score = (text_score + audio_score) / 2

    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    # update teacher_score_history list
    cursor.execute("SELECT teacher_score_history FROM cur_state")
    result = cursor.fetchone()
    if result:
        teacher_score_history = json.loads(result[0])
    else:
        teacher_score_history = []
    teacher_score_history.append(teacher_score)
    teacher_score_history = json.dumps(teacher_score_history)
    cursor.execute("UPDATE cur_state SET teacher_score_history = ?", (teacher_score_history,))
    # update teacher_score
    cursor.execute("UPDATE cur_state SET teacher_score = ?", (teacher_score,))
    db.commit()
    db.close()

def gen_student_emotion(latest_file):
    # 获取timestamp最近的文件
    # latest_file = sorted(os.listdir("pic"))[-1].split('.')[0]

    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    cursor.execute("SELECT latest_pic FROM cur_state")
    result = cursor.fetchone()
    db.close()
    if result and result[0] == latest_file: # 如果数据库中的latest_pic和文件夹中的一致
        print(f"{latest_file} has been processed, no need to update")
        return # 不需要更新

    new_files = []
    for filename in sorted(os.listdir("pic")):
        if result[0] < filename.split('.')[0] <= latest_file:
            new_files.append(filename.split('.')[0])
    print("student emotion pic", new_files)
    pic_emotion = {
        "pos_num": 0, 
        "neu_num": 0,
        "neg_num": 0
    }

    for filename in new_files:
        picpath = f"pic/{filename}.png"
        data = {
            "path": picpath
        }
        # 获取request的返回值
        response = requests.post("http://localhost:5002/pic", json=data)
        print(response.json())
        response = response.json()
        # {"Angry": 0, "Fear": 0, "Happy": 0, "Neutral": 0, "Sad": 0, "Surprise": 0}
        pos_cnt = response['Happy'] + response['Surprise']
        neg_cnt = response['Angry'] + response['Fear'] + response['Sad']
        neu_cnt = response['Neutral']
        pic_emotion['pos_num'] += pos_cnt
        pic_emotion['neu_num'] += neu_cnt
        pic_emotion['neg_num'] += neg_cnt

    pic_score = compute_score(pic_emotion['pos_num'], pic_emotion['neu_num'], pic_emotion['neg_num'])

    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    # update student_score_history list
    cursor.execute("SELECT student_score_history FROM cur_state")
    result = cursor.fetchone()
    if result:
        student_score_history = json.loads(result[0])
    else:
        student_score_history = []
    student_score_history.append(pic_score)
    student_score_history = json.dumps(student_score_history)
    cursor.execute("UPDATE cur_state SET student_score_history = ?", (student_score_history,))
    # update student_score
    cursor.execute("UPDATE cur_state SET student_score = ?", (pic_score,))
    db.commit()
    db.close()

def get_summary(history, mode="normal"): 
    # history: str without '\n'
    # mode: "normal" or "concise"
    if not history:
        return
    # ChatGLM服务器的IP地址和端口号
    SERVER_IP = '10.129.160.70'
    SERVER_PORT = 5088
    history = history.replace("\n", "。")
    
    # 每200个字就分割一次
    # history = [["老师讲了什么？", history[i:i+200]] for i in range(0, len(history), 200)]

    prompt = ""
    if mode == "normal":
        prompt = "请你扮演一个课程助教，简单概括一下老师刚才讲的内容。不超过50个字"
    elif mode == "concise":
        prompt = "请你扮演一个课程助教，简单概括一下老师刚才讲的内容。不超过20个字"

    data = {
        "prompt": prompt,
        "history": [["老师讲了什么？", history]]
    }
    print(data)
    response = requests.post(f"http://{SERVER_IP}:{SERVER_PORT}", json=data)
    return response.json()['response']

# 每1分钟text都更新一次Summary
def update_summary():
    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    # 获取summary和raw_text
    cursor.execute("SELECT summary, raw_text FROM cur_state")
    result = cursor.fetchone()
    db.close()

    summary = result[0] if result[0] else ""
    raw_text = result[1] if result[1] else ""


    TEXT_LIM = 200
    while len(raw_text) > TEXT_LIM:
        process_text = raw_text[:TEXT_LIM]
        raw_text = raw_text[TEXT_LIM:]
        summary += f"{get_summary(process_text)}。"

    sum_cnt = 0 # 精简summary的次数不能超过1次
    # 每TEXT_LIM个字分段一个summary, 精简summary
    while (len(summary) > TEXT_LIM) and (sum_cnt < 1):
        summary_list = [summary[i:i+TEXT_LIM] for i in range(0, len(summary), TEXT_LIM)]
        summary_list = [get_summary(summary, mode="concise") for summary in summary_list]
        summary = "。".join(summary_list)
        sum_cnt += 1

    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    # update summary and raw_text
    cursor.execute("UPDATE cur_state SET summary = ?", (summary,))
    cursor.execute("UPDATE cur_state SET raw_text = ?", (raw_text,))
    db.commit()
    db.close()

def handle_audio_and_text(latest_file):
    print(f"handle_audio_and_text: {latest_file}")
    # latest_file = sorted(os.listdir("audio"))[-1].split('.')[0]

    # 更新speed和audio_silence
    try:
        gen_middle_columm(latest_file)
    except Exception as e:
        print("gen_middle_columm error: ", e)
    
    # 更新teacher_score和teacher_score_history
    try:
        gen_teacher_emotion(latest_file)
    except Exception as e:
        print("get_teacher_emotion error: ", e)
    
    # 更新summary
    try:
        update_summary()
    except Exception as e:
        print("update_summary error: ", e)

    # 更新latest_audio为latest_file
    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    cursor.execute("UPDATE cur_state SET latest_audio = ?", (latest_file,))
    db.commit()
    db.close()
    
def handle_pic(latest_file):
    print(f"handle_pic: {latest_file}")
    # latest_file = sorted(os.listdir("pic"))[-1].split('.')[0]
    # 更新student_score和student_score_history
    try:
        gen_student_emotion(latest_file)
    except Exception as e:
        print("get_student_emotion error: ", e)
    # 更新latest_pic
    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    cursor.execute("UPDATE cur_state SET latest_pic = ?", (latest_file,))
    db.commit()
    db.close()

    print_database()

@app.route('/upload-mp3', methods=['POST'])
def upload_mp3():
    file = request.files['file']
    if file and file.filename.endswith('.wav'):
        file.save(f"audio/{file.filename}")
        
        # 访问全局锁
        if current_app.lock == 0:
            current_app.lock = 1
            try:
                p = multiprocessing.Process(target=convert_mp3_to_text, args=(f"audio/{file.filename}", "ifasr"))
                p.start()
                p.join(timeout=50)
                if p.is_alive():
                    print("科大讯飞语音转文本超时")
                    p.terminate()
                    p.join()
                    convert_mp3_to_text(f"audio/{file.filename}", "local")
            except Exception as e:
                print("科大讯飞出错", e)
                convert_mp3_to_text(f"audio/{file.filename}", "local")
            current_app.lock = 0
        else:
            try:
                convert_mp3_to_text(f"audio/{file.filename}", "local")
            except Exception as e:
                print("本地语音转文本出错", e)

        # remove mp3, save wav

        # asyncio.create_task(handle_audio_and_text())
        # executor.submit(handle_audio_and_text)
        # threading.Thread(target=handle_audio_and_text).start()

        try:
            handle_audio_and_text(file.filename.split('.')[0])
        except Exception as e:
            print("handle_audio_and_text error: ", e)
            # 更新latest_audio为latest_file
            db = sqlite3.connect('database.db')
            cursor = db.cursor()
            cursor.execute("UPDATE cur_state SET latest_audio = ?", (file.filename.split('.')[0],))
            db.commit()
            db.close()


        return 'MP3 file uploaded successfully.'
    else:
        return 'Invalid file or file format. MP3 file required.'

@app.route('/upload-image', methods=['POST'])
def upload_image():
    file = request.files['file']
    if file and file.filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
        file.save(f'pic/{file.filename}')
        
        # asyncio.create_task(handle_pic())
        # executor.submit(handle_pic)
        # threading.Thread(target=handle_pic).start()

        try:
            handle_pic(file.filename.split('.')[0])
        except Exception as e:
            print("upload image error", e)
            # 更新latest_pic
            db = sqlite3.connect('database.db')
            cursor = db.cursor()
            cursor.execute("UPDATE cur_state SET latest_pic = ?", (file.filename.split('.')[0],))
            db.commit()
            db.close()

        return 'Image file uploaded successfully.'
    else:
        return 'Invalid file or file format. Supported image formats: JPG, JPEG, PNG, GIF.'

import requests
@app.route('/question', methods=['GET'])
def gen_question():
    # ChatGLM服务器的IP地址和端口号
    SERVER_IP = '10.129.160.70'
    SERVER_PORT = 5088
    # curl -X POST "http://10.129.160.70:5088" -H 'Content-Type: application/json' -d '{"prompt": "你好", "history": []}'

    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    cursor.execute("SELECT summary FROM cur_state") 
    result = cursor.fetchone()
    history = result[0].replace("\n", "。") if result else ""
    db.close()

    if not history:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        return jsonify({"response": f"({timestamp})可分析的内容不足，请稍后再试"})
    
    data = {
        "prompt": "请你扮演一个课程学生，根据课程摘要的内容，简洁地提出三个问题，每个问题不超过20个字。",
        "history": [["课程摘要的内容是什么?", history]]
    }
    response = requests.post(f"http://{SERVER_IP}:{SERVER_PORT}", json=data)
    print(response.json())
    response = response.json()['response']
    result = {
        "response": response,
    }
    return jsonify(result)

@app.route('/summary', methods=['GET'])
def gen_summary():
    SERVER_IP = '10.129.160.70'
    SERVER_PORT = 5088
    # curl -X POST "http://10.129.160.70:5088" -H 'Content-Type: application/json' -d '{"prompt": "你好", "history": []}'
    
    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    cursor.execute("SELECT summary FROM cur_state")
    result = cursor.fetchone()
    history = result[0].replace("\n", "。") if result else ""
    db.close()

    if not history:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        return jsonify({"response": f"({timestamp})可分析的内容不足，请稍后再试"})

    data = {
        "prompt": "请你扮演一个课程助教，根据课程摘要的内容，简洁地进行总结，不超过100个字。",
        "history": [["课程摘要的内容是什么?", history]]
    }
    response = requests.post(f"http://{SERVER_IP}:{SERVER_PORT}", json=data)
    print(response.json())
    response = response.json()['response']
    result = {
        "response": response,
    }
    return jsonify(result)

@app.route('/speed', methods=['GET'])
def read_middle_columm():
    # read speed and audio_silence from database
    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    cursor.execute("SELECT speed, audio_silence FROM cur_state")
    result = cursor.fetchone()
    db.close()

    if result:
        return jsonify({
            "speech_rate": result[0],
            "audio_silence": result[1]
        })
    else:
        return jsonify({
            "speech_rate": 0,
            "audio_silence": 0
        })

@app.route('/teacher', methods=['GET'])
def read_teacher_emotion():
    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    cursor.execute("SELECT teacher_score FROM cur_state")
    result = cursor.fetchone()
    db.close()

    if result:
        return jsonify({
            "teacher_score": result[0]
        })
    else:
        return jsonify({
            "teacher_score": 0.5
        })

@app.route('/student', methods=['GET'])
def read_student_emotion():
    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    cursor.execute("SELECT student_score FROM cur_state")
    result = cursor.fetchone()
    db.close()

    if result:
        return jsonify({
            "student_score": result[0]
        })
    else:
        return jsonify({
            "student_score": 0.5
        })

@app.route('/his', methods=['GET'])
def get_history():
    # get student_score_history, teacher_score_history, latest_audio
    db = sqlite3.connect('database.db')
    cursor = db.cursor()
    cursor.execute("SELECT student_score_history, teacher_score_history, latest_pic FROM cur_state")
    result = cursor.fetchone()
    db.close()

    # return {'student_score_history': result[0], 'teacher_score_history': result[1], 'latest_audio': result[2]}


    if result:
        student = json.loads(result[0])
        teacher = json.loads(result[1])
        # 202305251415
        print(result[2])
        try:
            timestamp = int(result[2][-6:-2])
        except Exception as e:
            print("history error", e)
            timestamp = 0

        # for test
        # student = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.9, 0.8, 0.7, 0.6]
        # teacher = [0.5]
        # timestamp = 405

        # 将三个list的长度都限制在10以内，不足10的在前面补0
        student = [0] * max(0, 10 - len(student)) + student[-10:]
        teacher = [0] * max(0, 10 - len(teacher)) + teacher[-10:]
        
        # x 为过去10分钟的时间戳
        total_minutes = (timestamp // 100) * 60 + (timestamp % 100)
        x = []
        for i in range(10):
            x.append(f"{max(0, (total_minutes - 9 + i)) // 60:02d}:{max(0, (total_minutes -9 + i)) % 60:02d}")

        return jsonify({
            "student_score_history": student[-10:],
            "teacher_score_history": teacher[-10:],
            "x": x
        }) 
    else:
        return jsonify({
            "student_score_history": [0] * 10,
            "teacher_score_history": [0] * 10,
            "x": ["00:00"] * 10
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
