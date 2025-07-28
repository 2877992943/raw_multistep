from flask import Flask, request, jsonify
import base64
from PIL import Image
import io

app = Flask(__name__)

from uitar_history_toy import *
modelpath1 = '/root/autodl-tmp/yr/download_model/uitars-1.5-7b'

model, processor = get_model_proces(modelpath1)



import json
@app.route('/uitars', methods=['POST'])
def ground_image():
    # 获取JSON数据
    data = request.get_json()

    # # 检查数据是否包含必要的字段
    # if 'image' not in data or 'obj' not in data:
    #     return jsonify({'error': 'Missing image or task field'}), 400

    # # 获取图片和任务
    # image_base64 = data['image']
    # task = data['obj']
    # user_prompt = get_prompt(instruction)
    # messages = get_message(user_prompt)
    messages=data['message']
    #messages=json.load(messages)
    print(messages[0].keys())

    o=infer(messages,processor,model)

    # 将base64编码的图片解码
    #image_bytes = base64.b64decode(image_base64)
    #image = Image.open(io.BytesIO(image_bytes))



    # 将处理后的图片保存到内存中的BytesIO对象
    # img_byte_arr = io.BytesIO()
    # image.save(img_byte_arr, format='PNG')
    # img_byte_arr = img_byte_arr.getvalue()

    # 将处理后的图片编码为base64
    #processed_image_base64 = base64.b64encode(img_byte_arr).decode('utf-8')


    return jsonify({'uitars_output': o,
                    #'info':log1
                    })

if __name__ == '__main__':
    app.run(debug=True,port=6006,host='0.0.0.0')
