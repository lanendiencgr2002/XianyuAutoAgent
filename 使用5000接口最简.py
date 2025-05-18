import requests
from dataclasses import dataclass
from typing import Optional, Dict, Any
import time


@dataclass
class APIResponse:
    status: str
    time: float
    message: Optional[str] = None
    message_length: int = 0

@dataclass
class AIClient:
    @classmethod
    def ask(cls, url: str, key: str, model: str, question: str, system_prompt: str = "You are a helpful assistant. Use Chinese to respond.") -> Dict[str, Any]:
        start_time = time.time()
        try:
            response = cls.normal_ask(url, key, model, question, system_prompt)
            elapsed_time = time.time() - start_time
            return {
                "status": "success",
                "time": round(elapsed_time, 2),
                "message": response,
                "message_length": len(response) if response else 0
            }
        except Exception as e:
            print(f"测试接口出错: {str(e)}")
            return {
                "status": "error",
                "time": -1,
                "message": f"错误：{str(e)}",
                "message_length": 0
            }
    
    @classmethod
    def normal_ask(cls, url: str, key: str, model: str, question: str, system_prompt: str = "You are a helpful assistant. Use Chinese to respond.") -> str:
        url, payload, headers = cls._construct_requestall(url, key, model, system_prompt, question)
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"API请求失败: {response.text}")
        return cls._process_response(response)
    
    @classmethod
    def _process_response(cls, response) -> str:
        data = response.json()
        return data['choices'][0]['message']['content']
    
    @classmethod
    def _construct_requestall(cls, url: str, key: str, model: str, system_prompt: str, question: str):
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            "stream": False,
            "model": model,
            "temperature": 0.2,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "top_p": 1,
        }
        headers = {
            'accept': 'application/json',
            'authorization': f'Bearer {key}',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        return url, payload, headers

def 问ai(问题,系统提示词=None):
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    key = "ed8c2714-ecf3-4a0f-8732-9df9cf482de9"
    model = "doubao-1-5-vision-pro-32k-250115"
    默认系统提示词="You are a helpful assistant. Use Chinese to respond."
    默认问题="你好"
    url_param = url
    key_param = key
    model_param = model
    system_prompt=系统提示词 or 默认系统提示词
    req_param = 问题 or 默认问题

    response = AIClient.ask(
        url=url_param,
        key=key_param,
        model=model_param,
        question=req_param,
        system_prompt=system_prompt
    )
    print(response['message'])
    return response['message']

if __name__ == "__main__":
    问ai("今天天气好吗")
    print(type(问ai("今天天气好吗")))
