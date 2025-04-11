# app.py
from flask import Flask, jsonify, request, Response
from celery import Celery
import time

app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# 伪代码 - 大模型调用
def call_ai_model(prompt, task_type):
    # 这里应该是实际调用大模型的代码
    if task_type == "zh_to_en":
        return f"English translation of: {prompt}"
    elif task_type == "en_to_zh":
        return f"中文翻译: {prompt}"
    elif task_type == "summarize":
        return f"Summary: {prompt[:50]}..."
    return ""

# 1.1 获取所有功能列表接口
@app.route('/api/functions', methods=['GET'])
def get_functions():
    functions = [
        {"name": "zh_to_en", "description": "中文翻译为英文"},
        {"name": "en_to_zh", "description": "英文翻译为中文"},
        {"name": "summarize", "description": "文本总结"}
    ]
    return jsonify({"functions": functions})

# 1.2 调用具体功能接口（同步）
@app.route('/api/execute', methods=['POST'])
def execute_task():
    data = request.json
    task_type = data.get('task_type')
    text = data.get('text')
    
    if not task_type or not text:
        return jsonify({"error": "Missing parameters"}), 400
    
    result = call_ai_model(text, task_type)
    return jsonify({"result": result})

# 异步任务
@celery.task
def async_ai_task(task_type, text):
    time.sleep(5)  # 模拟耗时任务
    return call_ai_model(text, task_type)

# 异步任务提交
@app.route('/api/async_execute', methods=['POST'])
def async_execute():
    data = request.json
    task_type = data.get('task_type')
    text = data.get('text')
    
    if not task_type or not text:
        return jsonify({"error": "Missing parameters"}), 400
    
    task = async_ai_task.delay(task_type, text)
    return jsonify({"task_id": task.id}), 202

# 异步任务结果查询
@app.route('/api/async_result/<task_id>', methods=['GET'])
def get_async_result(task_id):
    task = async_ai_task.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'result': task.result
        }
    else:
        response = {
            'state': task.state,
            'status': str(task.info)
        }
    return jsonify(response)

# 流式返回接口
@app.route('/api/stream_execute', methods=['POST'])
def stream_execute():
    data = request.json
    task_type = data.get('task_type')
    text = data.get('text')
    
    def generate():
        # 模拟流式返回
        result = call_ai_model(text, task_type)
        for word in result.split():
            yield f"data: {word}\n\n"
            time.sleep(0.1)
    
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)