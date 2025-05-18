import time
from DrissionPage.common import Actions
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage import Chromium
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import urllib.parse

@dataclass
class Dp工具类:
    page: ChromiumPage
    def __post_init__(self):
        self.page = self.dp配置端口()
    @staticmethod
    def dp配置(端口:int=8077,默认超时时间:int=5):
        co = ChromiumOptions()
        co.set_local_port(端口)
        co.set_timeouts(base=默认超时时间)
        return ChromiumPage(addr_or_opts=co)
    @staticmethod
    def 根据标题取当前tab(page,标题):
        return next((tab for tab in page.get_tabs() if 标题 in tab.title), None)
    @staticmethod
    def 根据url获取当前tab(page,url):
        return next((tab for tab in page.get_tabs() if url in tab.url), None)
    @staticmethod
    def 返回最新tab(page):
        return page.latest_tab
    @staticmethod
    def dp配置使用手机环境测试():
        # 只在函数内部定义 user_agents，外部不可见
        user_agents = {
            "Chrome_Windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Firefox_Windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0",
            "Safari_macOS": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Version/15.1 Safari/537.36",
            "Edge_Windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Edge/110.0.1587.57",
            "Chrome_Android": "Mozilla/5.0 (Linux; Android 12; Pixel 5 Build/SP1A.210812.016) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Mobile Safari/537.36",
            "Safari_iOS": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Mobile/15E148 Safari/604.1",
            "Opera_Windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 OPR/97.0.4692.71"
        }
        co = ChromiumOptions().set_local_port(8077)
        co.set_user_agent(user_agents["Chrome_Android"])
        tab = Chromium(co).latest_tab

        zoom = {
            "command": "Emulation.setDeviceMetricsOverride",
            "parameters": {
                "width": 360,
                "height": 740,
                "deviceScaleFactor": 1,
                "mobile": True,
                "scale": 1
            }
        }
        tab.run_cdp(zoom["command"], **zoom["parameters"])
        tab.get("https://www.baidu.com/")
    @staticmethod
    def 通用等待(检查函数, 错误信息, 超时=10, 间隔=1):
        """
        通用等待函数：每隔一定时间检查一次检查函数，直到返回True或超时。
        :param 检查函数: 一个无参函数，返回True则结束等待
        :param 错误信息: 超时时抛出的错误信息
        :param 超时: 最大等待秒数
        :param 间隔: 每次检查的间隔秒数
        """
        结束时间 = time.time() + 超时
        最后异常 = None
        while time.time() < 结束时间:
            try:
                if 检查函数():
                    return
            except Exception as e:
                最后异常 = e
            time.sleep(间隔)
        # 超时后处理
        if 最后异常:
            raise Exception(f"{错误信息}，超时{超时}秒，最后异常：{最后异常}")
        else:
            raise TimeoutError(f"{错误信息}，超时{超时}秒，退出循环。")
    @staticmethod
    def 等待元素加载完成(page, 元素查找条件: str, 超时: int = 10):
        """
        等待页面元素加载完成

        :param page: ChromiumPage对象
        :param 元素查找条件: 元素的查找条件（如css选择器、xpath等）
        :param 超时: 最大等待秒数
        """
        def 检查元素存在() -> bool:
            try:
                page.ele(元素查找条件)
                return True
            except Exception:
                return False

        Dp工具类.通用等待(
            检查元素存在,
            f"等待元素加载完成：{元素查找条件}",
            超时
        )
    @staticmethod
    def 等待跳转到指定页面(page, 目标url列表, 超时=10):
        """等待页面跳转到目标URL"""
        def 检查页面URL():
            try:
                return page.url in 目标url列表
            except Exception:
                return False  # 发生异常时认为还未跳转到目标页面

        Dp工具类.通用等待(
            检查页面URL,
            f"等待跳转目标页面：{getattr(page, 'url', '未知')}",
            超时
        )

    @staticmethod
    def 打开指定页面并等待跳转到指定页面(page, 目标url, 超时=10):
        """打开页面并等待跳转到目标URL，成功返回True，超时返回False"""
        try:
            page.get(目标url)
            Dp工具类.等待跳转到指定页面(page, [目标url], 超时=超时)
            return True
        except Exception:
            return False

    @staticmethod
    def 找一个元素的属性(元素, 属性,条件=None):
        """查找元素属性"""
        try:
            if 条件 is None:
                return 元素.attr(属性)
            else:
                return 元素.ele(条件).attr(属性)
        except Exception:
            return None
    @staticmethod
    def 创建多个标签页对象(page,标签页数量=5):
        return [page.new_tab() for _ in range(标签页数量)]
    @staticmethod
    def 抓包(tab, 等待指定请求完成超时=4, 每个数据包等待时间=2, 等待直到以url开头出现=None):
        """
        通用抓包工具，监听并收集指定url前缀的数据包

        :param tab: ChromiumPage 的 tab 对象
        :param 等待指定请求完成超时: listen.wait_silent 的超时时间
        :param 每个数据包等待时间: listen.steps 的超时时间
        :param 等待直到以url开头出现: list[str]，只收集以这些前缀开头的url数据包，None表示全部收集
        :return: list，收集到的所有匹配数据包对象
        """
        if 等待直到以url开头出现 is None:
            等待直到以url开头出现 = []
        匹配数据包 = []
        tab.listen.start()
        try:
            tab.listen.wait_silent(timeout=等待指定请求完成超时)
            for i in tab.listen.steps(timeout=每个数据包等待时间):
                if not 等待直到以url开头出现 or any(i.url.startswith(prefix) for prefix in 等待直到以url开头出现):
                    匹配数据包.append(i)
        finally:
            tab.listen.stop()
        return 匹配数据包

def 获取所有商品url(page):
    找到所有商品卡片=page.eles('.cardWarp--dZodM57A')
    所有商品url=[i.ele('tag:a').attr('href') for i in 找到所有商品卡片]
    return 所有商品url

def 获取所有商品信息(page, urls, 线程数=2, json_path='商品信息.json'):
    def 获取商品信息(tab, url):
        tab.get(url)
        价格 = tab.ele('.price--OEWLbcxC windows--oJroL99y').text
        商品信息 = tab.ele('.desc--GaIUKUQY').text
        # 提取商品id
        query = urllib.parse.urlparse(url).query
        商品id = urllib.parse.parse_qs(query).get('id', [''])[0]
        print(商品信息[:10], 价格, 商品id)
        return {'url': url, '商品id': 商品id, '价格': 价格, '商品信息': 商品信息}
 

    tabs = Dp工具类.创建多个标签页对象(page, min(线程数, len(urls)))
    from itertools import cycle
    tab_cycle = cycle(tabs)
    results = []

    with ThreadPoolExecutor(max_workers=len(tabs)) as executor:
        # 提交所有任务
        future_to_url = {
            executor.submit(获取商品信息, tab, url): url
            for tab, url in zip(tab_cycle, urls)
        }
        # 收集所有结果
        for future in as_completed(future_to_url):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"抓取 {future_to_url[future]} 时出错: {e}")

    # 全部抓取完毕后写入json
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"已写入 {json_path}")

if __name__ == '__main__':
    page=Dp工具类.dp配置()
    print(Dp工具类.返回最新tab(page).title)
    url=Dp工具类.根据url获取当前tab(page,'https://www.goofish.com/personal')
    print(len(获取所有商品url(url)))
    获取所有商品信息(page,获取所有商品url(url))



