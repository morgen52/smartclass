# # # text classify
# # docker load -i text.tar
# docker run --rm -p 5000:5000 liminfinity/smartclass/text:0.0 python3 flask_server.py
# curl -X POST -H "Content-Type: application/json" -d '{"text":"你好"}' http://localhost:5000/text
# curl -X GET http://localhost:8000/speed
# curl -X POST "http://10.129.160.70:5088" -H 'Content-Type: application/json' -d '{"prompt": "请你扮演一个课程助教，根据授课内容，简洁地进行总结，不超过50个字。", "history": [["授课内容是什么", "理时有说与了随吉米不得科于预席。黩武子药都一语麟系口拟宇奇在里不要的世界复如透坏把记不爱都可子读联系后都琦在世界如同往记爱河里昏系。黩武子药都一语麟系口拟宇奇在里不要的世界复如透坏把记不爱都可子读联系后都琦在世界如同往记爱河里昏系。"]]}'

# conda activate smartclass
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python python3 ./data_server.py
