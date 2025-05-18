from flask import Flask, render_template, request, jsonify
import json 
from datetime import datetime
import re   
app = Flask(__name__)
验证码,验证码的时间=None,None
手机号='19860510350'

@app.route('/', methods=['POST'])
def 获取验证码():
    global 验证码,验证码的时间
    if request.method == 'POST':
        data = request.data.decode('utf-8')  # 将字节数据解码为字符串
        json_data = json.loads(data)  # 解析JSON数据
        text_content = json_data.get('text', '')
        print('收到的消息内容:',text_content)
        if '修改' not in text_content or '手机号' not in text_content or '账号安全' not in text_content:
            if '超职科技' in text_content and '同步使用' in text_content:
                if '请勿向任何人泄露' in text_content and '如非本人操作请忽略' in text_content:
                    if '验证码' in text_content:
                        获取验证码之后的字符串=text_content.split('验证码')[1]
                        # 直接匹配6位数字
                        验证码 = re.findall(r'\d{6}', 获取验证码之后的字符串)[0]
                        验证码的时间 = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        print(f"验证码: {验证码}, 验证码的时间: {验证码的时间}")
                        return jsonify({"message": "验证码已接收"})
        return jsonify({"message": "？？？"})

@app.route('/', methods=['GET'])
def 得到验证码和时间():
    global 验证码,验证码的时间
    return jsonify({
        "验证码": 验证码,
        "验证码的时间": 验证码的时间,
        "现在的时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=12568)
