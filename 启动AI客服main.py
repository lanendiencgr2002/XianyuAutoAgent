import base64  # 用于进行base64编码和解码
import json  # 用于处理JSON格式数据
import asyncio  # 提供异步IO支持，实现协程
import time  # 用于时间相关操作，如获取当前时间戳
import os  # 用于与操作系统交互，如读取环境变量
import websockets  # 用于WebSocket协议的异步通信
from loguru import logger  # 第三方日志库，便于记录和追踪日志
from dotenv import load_dotenv  # 用于加载.env文件中的环境变量
from XianyuApis import XianyuApis  # 闲鱼API接口封装类
from pathlib import Path
# 从自定义工具模块导入常用函数
from utils.xianyu_utils import generate_mid, generate_uuid, trans_cookies, generate_device_id, decrypt
from XianyuAgent参考 import XianyuReplyBot  # 闲鱼自动回复机器人
from context_manager import ChatContextManager  # 聊天上下文管理器
from ai_api import 问ai
from datetime import datetime
import requests
# 转到当前目录
os.chdir(Path(__file__).parent)
# 当前文件所在目录
print('当前文件所在目录：',Path(__file__).parent)
# 当前工作目录
print('当前工作目录：',os.getcwd())
# 当前目录以下文件
print('当前目录以下文件：',os.listdir(Path(__file__).parent))

超级简历验证码=None
class XianyuLive:
    def __init__(self, cookies_str):
        self.xianyu = XianyuApis()  # 初始化API接口对象
        self.base_url = 'wss://wss-goofish.dingtalk.com/'  # WebSocket服务器地址
        self.cookies_str = cookies_str  # 原始cookie字符串
        self.cookies = trans_cookies(cookies_str)  # 解析cookie字符串为字典
        self.myid = self.cookies['unb']  # 当前用户ID，从cookie中获取
        self.device_id = generate_device_id(self.myid)  # 生成设备ID，保证唯一性
        self.context_manager = ChatContextManager()  # 初始化聊天上下文管理器
        
        # 心跳相关配置
        self.heartbeat_interval = 15  # 心跳包发送间隔（秒）
        self.heartbeat_timeout = 5    # 心跳包超时时间（秒）
        self.last_heartbeat_time = 0  # 上次心跳包发送时间戳
        self.last_heartbeat_response = 0  # 上次收到心跳响应的时间戳
        self.heartbeat_task = None  # 心跳任务对象
        self.ws = None  # WebSocket连接对象
        # 加载商品信息json
        # 这里还要兼容服务器上的商品信息.json
        try:
            path=os.path.join(os.getcwd(),'商品信息.json')
            print(path)
            with open(path, 'r', encoding='utf-8') as f:
                商品信息列表 = json.load(f)
            # ids:{json字典}
            self.商品信息字典 = {item['商品id']: item for item in 商品信息列表}
            logger.info("XianyuAutoAgent 商品信息.json文件存在")
        except Exception as e:
            logger.info("XianyuAutoAgent 商品信息.json文件不存在")
            logger.error(f" 商品信息.json文件不存在: {e}")
           
    async def send_msg(self, ws, cid, toid, text):
        """
        发送聊天消息到指定用户（闲鱼WebSocket接口）。

        该方法将文本消息封装为指定格式，进行base64编码后，通过WebSocket连接发送给目标用户。消息体包含会话ID、接收者ID、消息内容等必要信息，适用于闲鱼IM协议的单聊场景。

        Args:
            ws (websockets.WebSocketClientProtocol): 已建立的WebSocket连接对象，用于消息发送。
            cid (str): 会话ID（通常为目标用户ID），用于标识聊天会话。
            toid (str): 目标用户ID，消息实际接收者。
            text (str): 需要发送的文本内容。

        Returns:
            None: 此方法为异步方法，无返回值。

        Raises:
            Exception: 发送过程中如WebSocket断开、序列化失败等异常会被抛出。

        Examples:
            >>> await xianyu_live.send_msg(ws, "123456", "654321", "你好，请问还在吗？")
            # 发送一条文本消息到用户654321

        Notes:
            - 消息内容会被base64编码，防止传输过程中的格式问题。
            - 发送者自己也会作为实际接收者之一，便于消息同步。
            - 该方法假设ws已处于连接状态。

        See Also:
            - XianyuLive.init: 用于初始化WebSocket连接。
            - XianyuLive.is_chat_message: 判断消息类型的辅助方法。

        Warnings:
            - 如果ws未连接或已断开，调用此方法会抛出异常。
            - 请确保传入的cid和toid为合法的闲鱼用户ID字符串。

        """
        text = {
            "contentType": 1,  # 消息内容类型，1表示文本
            "text": {
                "text": text  # 实际发送的文本内容
            }
        }
        # 对消息内容进行base64编码，防止传输过程中的格式问题
        text_base64 = str(base64.b64encode(json.dumps(text).encode('utf-8')), 'utf-8')
        msg = {
            "lwp": "/r/MessageSend/sendByReceiverScope",  # 协议字段，指定消息发送接口
            "headers": {
                "mid": generate_mid()  # 生成唯一消息ID
            },
            "body": [
                {
                    "uuid": generate_uuid(),  # 生成唯一消息UUID
                    "cid": f"{cid}@goofish",  # 会话ID，格式为"用户ID@goofish"
                    "conversationType": 1,  # 会话类型，1表示单聊
                    "content": {
                        "contentType": 101,  # 自定义内容类型
                        "custom": {
                            "type": 1,  # 自定义类型，1表示文本
                            "data": text_base64  # base64编码后的消息内容
                        }
                    },
                    "redPointPolicy": 0,  # 红点策略，0为默认
                    "extension": {
                        "extJson": "{}"  # 扩展字段，预留
                    },
                    "ctx": {
                        "appVersion": "1.0",  # 应用版本
                        "platform": "web"  # 平台类型
                    },
                    "mtags": {},  # 消息标签，预留
                    "msgReadStatusSetting": 1  # 消息已读状态设置
                },
                {
                    "actualReceivers": [
                        f"{toid}@goofish",  # 实际接收者ID
                        f"{self.myid}@goofish"  # 发送者自己也作为接收者
                    ]
                }
            ]
        }
        await ws.send(json.dumps(msg))  # 通过WebSocket发送消息

    async def init(self, ws):
        # 初始化WebSocket连接，注册并同步状态
        token = self.xianyu.get_token(self.cookies, self.device_id)['data']['accessToken']  # 获取访问令牌
        msg = {
            "lwp": "/reg",  # 注册协议字段
            "headers": {
                "cache-header": "app-key token ua wv",  # 缓存相关header
                "app-key": "444e9908a51d1cb236a27862abc769c9",  # 应用key
                "token": token,  # 访问令牌
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 DingTalk(2.1.5) OS(Windows/10) Browser(Chrome/133.0.0.0) DingWeb/2.1.5 IMPaaS DingWeb/2.1.5",  # 用户代理
                "dt": "j",  # 设备类型
                "wv": "im:3,au:3,sy:6",  # 版本信息
                "sync": "0,0;0;0;0;",  # 同步参数
                "did": self.device_id,  # 设备ID
                "mid": generate_mid()  # 消息ID
            }
        }
        await ws.send(json.dumps(msg))  # 发送注册消息
        # 等待一段时间，确保连接注册完成
        await asyncio.sleep(1)
        # 发送同步状态确认包
        msg = {"lwp": "/r/SyncStatus/ackDiff", "headers": {"mid": "5701741704675979 0"}, "body": [
            {"pipeline": "sync", "tooLong2Tag": "PNM,1", "channel": "sync", "topic": "sync", "highPts": 0,
             "pts": int(time.time() * 1000) * 1000, "seq": 0, "timestamp": int(time.time() * 1000)}]}
        await ws.send(json.dumps(msg))
        logger.info('连接注册完成')  # 日志记录注册完成

    def is_chat_message(self, message):
        """判断消息是否为用户聊天消息"""
        try:
            return (
                isinstance(message, dict)  # 必须是字典类型
                and "1" in message 
                and isinstance(message["1"], dict)  # message["1"]也必须是字典
                and "10" in message["1"]
                and isinstance(message["1"]["10"], dict)  # message["1"]["10"]也必须是字典
                and "reminderContent" in message["1"]["10"]  # 包含聊天内容字段
            )
        except Exception:
            return False  # 任一条件不满足则不是聊天消息

    def is_sync_package(self, message_data):
        """判断消息是否为同步包"""
        try:
            return (
                isinstance(message_data, dict)
                and "body" in message_data
                and "syncPushPackage" in message_data["body"]
                and "data" in message_data["body"]["syncPushPackage"]
                and len(message_data["body"]["syncPushPackage"]["data"]) > 0
            )
        except Exception:
            return False
    
    def _获取超级简历验证码(self, timeout: float = 15.0, interval: float = 1.0):
        print("开始获取验证码")
        global 超级简历验证码
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                post_data = self._得到验证码和时间()
            except Exception as e:
                time.sleep(interval)
                continue
            if post_data['验证码'] != 超级简历验证码:
                超级简历验证码 = post_data['验证码']
                now_str = post_data['现在的时间']
                code_time_str = post_data['验证码的时间']
                # 假设格式为 "2025-05-18 22:29:58"
                fmt = "%Y-%m-%d %H:%M:%S"
                now = datetime.strptime(now_str, fmt)
                code_time = datetime.strptime(code_time_str, fmt)
                diff_seconds = (now - code_time).total_seconds()
                # 如果相差时间超过5分钟 则返回None
                if diff_seconds > 300:return None,None
                return post_data['验证码'], diff_seconds
            time.sleep(interval)
        return None,None
    
    def _得到验证码和时间(self):
        # 发送get请求 获取验证码
        host='http://localhost:12568'
        response=requests.get(host)
        return response.json()

    def is_typing_status(self, message):
        """判断消息是否为用户正在输入状态"""
        try:
            return (
                isinstance(message, dict)
                and "1" in message
                and isinstance(message["1"], list)
                and len(message["1"]) > 0
                and isinstance(message["1"][0], dict)
                and "1" in message["1"][0]
                and isinstance(message["1"][0]["1"], str)
                and "@goofish" in message["1"][0]["1"]
            )
        except Exception:
            return False

    async def handle_message(self, message_data, websocket):
        """处理所有类型的消息，包括聊天、订单、同步等"""
        try:
            # 发送ACK响应
            await self._send_ack_response(message_data, websocket)
            
            # 如果不是同步包消息，直接返回
            if not self.is_sync_package(message_data):
                return

            # 获取并解密消息数据
            message = await self._decrypt_sync_data(message_data)
            if not message:
                return
                
            # 判断消息类型
            if self.is_typing_status(message):
                return
            elif not self.is_chat_message(message):
                return
        except Exception as e:
            logger.error(f"处理消息时发生错误: {str(e)}")
            logger.debug(f"原始消息: {message_data}")
        try:
            # 处理聊天消息
            await self._process_chat_message(message, websocket)
        except Exception as e:
            logger.error(f"处理聊天消息时发生错误: {str(e)}")
            logger.debug(f"原始消息: {message_data}")
            


    async def _send_ack_response(self, message_data, websocket):
        """发送ACK响应确认收到消息"""
        try:
            message = message_data
            ack = {
                "code": 200,
                "headers": {
                    "mid": message["headers"]["mid"] if "mid" in message["headers"] else generate_mid(),
                    "sid": message["headers"]["sid"] if "sid" in message["headers"] else '',
                }
            }
            # 复制其他可能的header字段
            for key in ["app-key", "ua", "dt"]:
                if key in message["headers"]:
                    ack["headers"][key] = message["headers"][key]
            await websocket.send(json.dumps(ack))
        except Exception:
            pass  # ACK失败不影响后续处理

    async def _decrypt_sync_data(self, message_data):
        """解密同步包数据"""
        try:
            sync_data = message_data["body"]["syncPushPackage"]["data"][0]
            
            # 检查是否有必要的字段
            if "data" not in sync_data:
                logger.debug("同步包中无data字段")
                return None

            # 解密数据
            data = sync_data["data"]
            try:
                data = base64.b64decode(data).decode("utf-8")  # 尝试base64解码
                data = json.loads(data)  # 解码后转为JSON对象
                return None
            except Exception:
                decrypted_data = decrypt(data)  # 若解码失败则尝试自定义解密
                return json.loads(decrypted_data)  # 解密后转为JSON对象
        except Exception as e:
            logger.error(f"消息解密失败: {e}")
            return None

    async def 自身消息测试(self,send_user_name,send_user_id,send_message,url_info,item_id,websocket,cid,myid):
        """测试是否为自身消息的方法"""
        if send_user_id != myid:return
        await self.send_msg(websocket, cid, send_user_id, '我该说啥呢')

        # 超级简历验证码特殊情况
        if send_message == '1':
            await self.send_msg(websocket, cid, send_user_id, '开始测试')
            await self.send_msg(websocket, cid, send_user_id, "手机号：19860510350 发送验证码后10秒，现在才返回你验证码，请等一会")
            阻塞获取验证码, _ = self._获取超级简历验证码()
            if 阻塞获取验证码:
                await self.send_msg(websocket, cid, send_user_id, "验证码："+阻塞获取验证码)
            else:
                await self.send_msg(websocket, cid, send_user_id, "验证码获取失败你小子可能没用我手机发验证码哦，请联系管理员电话13631902746 wx：lanendiencgr")
            await self.send_msg(websocket, cid, send_user_id, '测试结束')
        
        # 测试订单状态的超级简历vip
        if send_message == '2':
            try:
                await self.send_msg(websocket, cid, send_user_id, '开始测试')
                # 向数据库加一个订单
                self.context_manager.add_order('666', '666', 0.8, "超级简历vip", 1, 1, send_user_name)
                # 查询订单
                orders = self.context_manager.get_order('666', '666')
                if orders:
                    print(orders)
                    created_at = orders['created_at']
                    if isinstance(created_at, str):
                        # 假设格式为 "2025-05-26T02:47:42.508040"
                        created_at = datetime.fromisoformat(created_at)
                        print('创建日',created_at.strftime("%Y-%m-%d"))
                        print('现在日',datetime.now().strftime("%Y-%m-%d"))
                    if created_at.strftime("%Y-%m-%d") != datetime.now().strftime("%Y-%m-%d"):
                        await self.send_msg(websocket, cid, send_user_id, "订单创建时间不是今天")
                    else:
                        await self.send_msg(websocket, cid, send_user_id, "订单创建时间是今天")
                else:
                    await self.send_msg(websocket, cid, send_user_id, "没有找到订单")
                await self.send_msg(websocket, cid, send_user_id, '测试结束')
            except Exception as e:
                logger.error(f"测试订单状态时发生错误: {e}")
        
        # 测试时间
        if send_message == '3':
            # 查询666,666订单
            orders = self.context_manager.get_order('666', '666')
            if orders:
                created_at = orders['created_at']
                if isinstance(created_at, str):
                    # 假设格式为 "2025-05-26T02:47:42.508040"
                    created_at = datetime.fromisoformat(created_at)
                if created_at.strftime("%Y-%m-%d") != datetime.now().strftime("%Y-%m-%d"):
                    await self.send_msg(websocket, cid, send_user_id, "订单创建时间不是今天")
                else:
                    await self.send_msg(websocket, cid, send_user_id, "订单创建时间是今天")
            else:
                await self.send_msg(websocket, cid, send_user_id, "没有找到订单")
            await self.send_msg(websocket, cid, send_user_id, '测试结束')


        pass

    async def _process_chat_message(self, message, websocket):
        """处理聊天消息"""
        # 提取消息基本信息
        create_time = int(message["1"]["5"])  # 消息创建时间戳
        send_user_name = message["1"]["10"]["reminderTitle"]  # 发送者昵称
        send_user_id = message["1"]["10"]["senderUserId"]  # 发送者用户ID
        send_message = message["1"]["10"]["reminderContent"]  # 聊天内容
        cid = message["1"]["2"].split('@')[0]  # 会话ID
        url_info = message["1"]["10"]["reminderUrl"]  # 商品链接
        item_id = url_info.split("itemId=")[1].split("&")[0] if "itemId=" in url_info else None  # 提取商品ID
        
        # 基本验证
        if not item_id:
            return
        
        await self.自身消息测试(send_user_name,send_user_id,send_message,url_info,item_id,websocket,cid,self.myid)
        if send_user_id == self.myid:
            return  # 过滤自身消息
        # 以下都是别人的消息

        # 处理走关系通道
        if await self._handle_走关系通道(item_id, send_message, cid, send_user_id, websocket):
            return
        
        # 处理订单状态消息
        if await self._handle_order_status(message, cid, send_user_id, item_id, websocket,send_user_name):
            return
        
        # 处理特殊码信息，比如666这种关键信息
        if await self._handle_已付款今天关键消息(item_id, send_user_id, send_user_name, send_message, cid, websocket):
            return

        # 时效性验证（过滤5分钟前消息）
        if (time.time() * 1000 - create_time) > 300000:
            logger.debug("当前消息是5分钟前，过期消息丢弃")
            return
        
        # 获取商品信息并生成回复 兜底方案
        await self._generate_and_send_reply(item_id, send_user_id, send_user_name, send_message, cid, websocket)

    async def _handle_已付款今天关键消息(self, item_id, send_user_id, send_user_name, send_message, cid, websocket):
        """处理特殊码信息，比如666这种关键信息"""
        # 查询订单是否付款
        orders = self.context_manager.get_order(send_user_id, item_id)
        # 判断现在的时间是不是付款当天 2025-05-26T02:47:42.508040 
        if not orders: # 不存在订单
            return False
        if orders['is_paid'] != 1: # 订单未付款
            return False
        created_at = orders['created_at']
        if isinstance(created_at, str):
            # 假设格式为 "2025-05-26T02:47:42.508040"
            created_at = datetime.fromisoformat(created_at)
        if created_at.strftime("%Y-%m-%d") != datetime.now().strftime("%Y-%m-%d"): # 订单不是今天付款的
            return False
        if await self._处理超级简历特殊今天关键信息(item_id, send_user_id, send_user_name, send_message, cid, websocket):
            return True
        return False
    async def _处理超级简历特殊今天关键信息(self, item_id, send_user_id, send_user_name, send_message, cid, websocket):
        """处理超级简历特殊今天关键信息"""
        超级简历_msg_prefix = "（付款后一天内发我666我还会回你验证码）"
        admin_contact = "请联系管理员电话13631902746 wx：lanendiencgr"
        if item_id == "926003417058":
            if send_message == '666':
                验证码, _ = self._获取超级简历验证码()
                if 验证码:
                    await self.send_msg(websocket, cid, send_user_id, f"{超级简历_msg_prefix}验证码：{验证码}")
                else:
                    await self.send_msg(websocket, cid, send_user_id, f"{超级简历_msg_prefix}验证码获取失败你小子可能没用我手机发验证码哦，如果还不行{admin_contact}")
        return False

    async def _handle_走关系通道(self, item_id, send_message, cid, send_user_id, websocket):
        """处理走关系通道相关逻辑"""
        if item_id == "926003417058":
            if send_message == 'lanendiencgr':
                await self.send_msg(websocket, cid, send_user_id, "手机号：19860510350 发送验证码后10秒，现在才返回你验证码，请等一会")
                阻塞获取验证码, _ = self._获取超级简历验证码()
                if 阻塞获取验证码:
                    await self.send_msg(websocket, cid, send_user_id, "验证码："+阻塞获取验证码)
                else:
                    await self.send_msg(websocket, cid, send_user_id, "验证码获取失败你小子可能没用我手机发验证码哦，请联系管理员电话13631902746 wx：lanendiencgr")
                return True
        return False

    async def _handle_order_status(self, message, cid, send_user_id, item_id, websocket,send_user_name):
        """处理订单状态相关逻辑"""
        try:
            task_name = json.loads(message["1"]["10"]['bizTag']).get('taskName', '')
            
            # 处理已拍下未付款状态
            if any(x in task_name for x in ['已拍下', '未付款']):
                await self.send_msg(websocket, cid, send_user_id, "感谢您的拍下，祝您万事如意，付款后立刻安排发货！")
                self.context_manager.add_order(send_user_id, item_id, self.商品信息字典[item_id]['价格'], self.商品信息字典[item_id]['商品信息'], 1,  0, send_user_name)
                if item_id == "926003417058":
                    await self.send_msg(websocket, cid, send_user_id, "手机号：19860510350 尽快付款获取验证码登录")
                return True
            
            # 处理已付款待发货状态
            if any(x in task_name for x in ['已付款', '待发货']):
                await self.send_msg(websocket, cid, send_user_id, "等我发货")
                self.context_manager.add_order(send_user_id, item_id, self.商品信息字典[item_id]['价格'], self.商品信息字典[item_id]['商品信息'], 1, 1, send_user_name)
                if item_id == "926003417058":
                    print("开始获取验证码")
                    阻塞获取验证码, _ = self._获取超级简历验证码()
                    if 阻塞获取验证码:
                        await self.send_msg(websocket, cid, send_user_id, "（付款后一天内发我666我还会回你验证码）验证码："+阻塞获取验证码)
                    else:
                        await self.send_msg(websocket, cid, send_user_id, "（付款后一天内发我666我还会回你验证码）验证码获取失败你小子可能没用我手机发验证码哦，如果还不行请联系管理员电话13631902746 wx：lanendiencgr")
                return True
        except Exception as e:
            logger.debug(f"解析bizTag出错: {e}")
        
        return False

    async def _generate_and_send_reply(self, item_id, send_user_id, send_user_name, send_message, cid, websocket):
        """生成并发送AI回复"""
        try:
            # 获取商品信息
            item_info = self.get_item_info_from_json_or_api(item_id)
            item_description = f"{item_info['desc']};当前商品售卖价格为:{str(item_info['soldPrice'])}"
            
            logger.info(f"user: {send_user_name}, 发送消息: {send_message} 商品id: {item_id} 价格: {item_info['soldPrice']}")
            
            # 添加用户消息到上下文
            self.context_manager.add_message(send_user_id, item_id, "user", send_message)
            
            # 获取完整的对话上下文
            context = self.context_manager.get_context(send_user_id, item_id)
            
            # 构建提示词
            prompt = (
                f"商品描述：{item_description}\n"+
                f"当前商品售卖价格为:{str(item_info['soldPrice'])}\n"+
                f"用户{send_user_name} 发送消息: {send_message}\n"+
                f"历史对话上下文：{context}"
            )

            # 调用AI生成回复
            bot_reply = 问ai(prompt, "你是咸鱼客服自动回复机器人，帮我回答用户的问题")
            
            # 发送回复
            await self.send_msg(websocket, cid, send_user_id, '（自动回复）：'+bot_reply)
            
            # 添加机器人回复到上下文
            self.context_manager.add_message(send_user_id, item_id, "assistant", bot_reply)
        except Exception as e:
            logger.error(f"生成回复时发生错误: {str(e)}")

    async def send_heartbeat(self, ws):
        """发送心跳包并等待响应，保持连接活跃"""
        try:
            # 生成唯一的消息ID，用于标识本次心跳包
            heartbeat_mid = generate_mid()
            # 构造心跳包消息体，lwp为协议字段，headers中包含消息ID
            heartbeat_msg = {
                "lwp": "/!",
                "headers": {
                    "mid": heartbeat_mid
                }
            }
            # 通过WebSocket发送心跳包，保持与服务器的连接活跃
            await ws.send(json.dumps(heartbeat_msg))
            # 记录本次心跳包发送的时间，用于后续超时判断
            self.last_heartbeat_time = time.time()
            logger.debug("心跳包已发送")
            # 返回本次心跳包的消息ID，便于后续匹配响应
            return heartbeat_mid
        except Exception as e:
            # 捕获并记录发送心跳包过程中出现的异常
            logger.error(f"发送心跳包失败: {e}")
            # 向上抛出异常，通知调用方处理
            raise

    async def heartbeat_loop(self, ws):
        """心跳维护循环，定时发送心跳包并检测连接状态"""
        while True:
            try:
                current_time = time.time()  # 获取当前时间戳
                
                # 检查是否需要发送心跳
                if current_time - self.last_heartbeat_time >= self.heartbeat_interval:
                    await self.send_heartbeat(ws)
                
                # 检查上次心跳响应时间，如果超时则认为连接已断开
                if (current_time - self.last_heartbeat_response) > (self.heartbeat_interval + self.heartbeat_timeout):
                    logger.warning("心跳响应超时，可能连接已断开")
                    break
                
                await asyncio.sleep(1)  # 每秒检查一次
            except Exception as e:
                logger.error(f"心跳循环出错: {e}")
                break

    async def handle_heartbeat_response(self, message_data):
        """处理心跳响应，刷新心跳时间"""
        try:
            if (
                isinstance(message_data, dict)
                and "headers" in message_data
                and "mid" in message_data["headers"]
                and "code" in message_data
                and message_data["code"] == 200
            ):
                self.last_heartbeat_response = time.time()  # 刷新心跳响应时间
                logger.debug("收到心跳响应")
                return True
        except Exception as e:
            logger.error(f"处理心跳响应出错: {e}")
        return False

    async def main(self):
        # 主循环，负责WebSocket连接、消息收发和重连
        while True:
            try:
                headers = {
                    "Cookie": self.cookies_str,  # 登录cookie
                    "Host": "wss-goofish.dingtalk.com",  # 服务器主机名
                    "Connection": "Upgrade",  # 升级为WebSocket协议
                    "Pragma": "no-cache",  # 禁用缓存
                    "Cache-Control": "no-cache",  # 禁用缓存
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",  # 浏览器标识
                    "Origin": "https://www.goofish.com",  # 请求来源
                    "Accept-Encoding": "gzip, deflate, br, zstd",  # 支持的压缩格式
                    "Accept-Language": "zh-CN,zh;q=0.9",  # 支持的语言
                }

                async with websockets.connect(self.base_url, extra_headers=headers) as websocket:
                    self.ws = websocket  # 保存WebSocket对象
                    await self.init(websocket)  # 初始化连接
                    
                    # 初始化心跳时间
                    self.last_heartbeat_time = time.time()
                    self.last_heartbeat_response = time.time()
                    
                    # 启动心跳任务
                    self.heartbeat_task = asyncio.create_task(self.heartbeat_loop(websocket))
                    
                    async for message in websocket:
                        try:
                            message_data = json.loads(message)  # 解析收到的消息
                            
                            # 处理心跳响应
                            if await self.handle_heartbeat_response(message_data):
                                continue
                            
                            # 处理其他消息
                            await self.handle_message(message_data, websocket)
                                
                        except json.JSONDecodeError:
                            logger.error("消息解析失败")
                        except Exception as e:
                            logger.error(f"处理消息时发生错误: {str(e)}")
                            logger.debug(f"原始消息: {message}")

            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket连接已关闭")
                if self.heartbeat_task:
                    self.heartbeat_task.cancel()
                    try:
                        await self.heartbeat_task
                    except asyncio.CancelledError:
                        pass
                await asyncio.sleep(5)  # 等待5秒后重连
                
            except Exception as e:
                logger.error(f"连接发生错误: {e}")
                if self.heartbeat_task:
                    self.heartbeat_task.cancel()
                    try:
                        await self.heartbeat_task
                    except asyncio.CancelledError:
                        pass
                await asyncio.sleep(5)  # 等待5秒后重连

    def get_item_info_from_json_or_api(self, item_id):
        item = self.商品信息字典.get(item_id)
        if item:
            # 读取商品信息字典成功！
            logger.info(f"读取商品信息字典成功！商品信息：{item['商品信息']} 价格：{item['价格']}")
            return {
                "desc": item["商品信息"],
                "soldPrice": float(item["价格"])
            }
        else:
            # 当前是未知商品
            logger.error(f"当前是未知商品：{item_id}")
            # 尝试走原有API
            try:
                return self.xianyu.get_item_info(self.cookies, item_id)['data']['itemDO']
            except Exception as e:
                logger.error(f"获取商品信息失败: {e}")
                return {
                    "desc": "商品信息获取失败",
                    "soldPrice": 0
                }

if __name__ == '__main__':
    # 加载环境变量中的cookie字符串
    load_dotenv()  # 加载.env文件
    cookies_str = os.getenv("COOKIES_STR")  # 获取COOKIES_STR环境变量
    # bot = XianyuReplyBot()  # 初始化自动回复机器人（如需手动实例化可取消注释）
    xianyuLive = XianyuLive(cookies_str)  # 创建XianyuLive实例
    # 常驻进程，启动主循环
    asyncio.run(xianyuLive.main())
