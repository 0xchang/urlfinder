#!/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2023/3/23 20:05
@author: 0xchang
@E-mail: oxchang@163.com
@file: urlfinder.py
@Github: https://github.com/0xchang
"""
import argparse
import time
from concurrent.futures import ThreadPoolExecutor
import threading
import toml
import colorama
import requests
import queue
import re

lock = threading.Lock()
Urlque = queue.Queue(500)
colorama.init(autoreset=True)


def inputwhite(url: str):
    global baseurl
    global baseip
    global urlfilter
    # 添加自定义白名单到网页
    if url.startswith('http://') or url.startswith('https://'):
        pass
    else:
        url = 'http://' + url
    if not url.endswith('/'):
        url += '/'
    with lock:
        baseurl = re.search('https?://[0-9a-zA-Z.-]*/', url).group(0)
        baseurl = baseurl[:-1]
        ip_pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        domain_pattern = r"(?<=://)([^/]+\.)?([^./]+\.[^./]+)(?=/)?"
        ip = re.search(ip_pattern, url)
        domain = re.search(domain_pattern, url)
        if ip:
            baseip = ip.group(0)
            print("IP地址：", ip.group())
        elif domain:
            baseip = domain.group(2)
            print("域名：", domain.group(2))
    for w in config.get('white'):
        u = baseurl + '/' + w
        if not u in urlfilter:
            urlfilter.add(u)
            Urlque.put(u)


def getdata(url: str):
    global count
    global baseip
    global urlfilter
    if count == 0:
        return
    # 后缀检测,如果在黑名单中,则不访问该网站
    for end in blacklist:
        if url.endswith(end):
            return
    with lock:
        count -= 1
    headers = config.get('headers')
    timeout = config.get('timeout')
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if not url in urlfilter:
            urlfilter.add(url)
        with lock:
            if resp.status_code == 200:
                print(colorama.Fore.LIGHTGREEN_EX + '[{}]: {:<80}'.format(resp.status_code,
                                                                          url) + ' ' * 5 + f'{len(resp.content)}B')
            elif resp.status_code == 400:
                print(colorama.Fore.LIGHTYELLOW_EX + '[{}]: {:<80}'.format(resp.status_code,
                                                                           url) + ' ' * 5 + f'{len(resp.content)}B')
            else:
                print(colorama.Fore.MAGENTA + '[{}]: {:<80}'.format(resp.status_code,
                                                                    url) + ' ' * 5 + f'{len(resp.content)}B')
        for ru in rules:
            urls = re.findall(ru, resp.text)
            for u in urls:
                u: str
                if u.startswith('//'):
                    if baseip in u:
                        if baseurl.startswith('https'):
                            u = 'https:' + u
                        elif baseurl.startswith('http'):
                            u = 'http:' + u
                        # print(u)
                elif u.startswith('/'):
                    u = baseurl + u

                else:
                    if baseip in u:
                        # print(u)
                        pass
                if not u in urlfilter and not u.startswith('//') and baseip in u:
                    with lock:
                        # print(u)
                        # print(baseurl + u)
                        for end in blacklist:
                            if u.endswith(end):
                                flag = True
                                break
                            else:
                                flag = False
                        if not flag:
                            print(u)
                            Urlque.put(u)
                            urlfilter.add(u)
    except requests.exceptions.ConnectionError:
        with lock:
            print(colorama.Fore.RED + '[+]Connection Error:', url)
            # print()


def banner():
    text = '''
            _ _____ _           _
 _   _ _ __| |  ___(_)_ __   __| | ___ _ __
| | | | '__| | |_  | | '_ \ / _` |/ _ \ '__|
| |_| | |  | |  _| | | | | | (_| |  __/ |
 \__,_|_|  |_|_|   |_|_| |_|\__,_|\___|_|
'''
    print(colorama.Fore.GREEN + text + ' ' * 27 + 'Version 0.0.1')
    print(colorama.Fore.GREEN + 'start...\nload config...')


if __name__ == '__main__':
    starttime = time.time()
    banner()
    config = toml.load('config.toml')
    print(config)

    baseurl = ''
    baseip = ''
    urlfilter = set()
    blacklist = config.get('black')
    rules = config.get('rule')
    parse = argparse.ArgumentParser()
    parse.add_argument('-u', '--url', help='target url', required=True)
    # 设置最多访问多少个子链接
    parse.add_argument('-c', '--count', help='degree of depth', default=25, type=int)
    args = parse.parse_args()
    count = args.count
    Urlque.put(args.url)
    with ThreadPoolExecutor(max_workers=config.get('thread')) as executor:
        # 将白名单添加到任务中
        executor.submit(inputwhite, args.url)
        while True:
            if Urlque.empty() or count == 0:
                break
            url = Urlque.get()
            executor.submit(getdata, url)
            # 控制频率，如果为空，程序太快导致无法访问后续url
            time.sleep(config.get('delay'))
        executor.shutdown(wait=True)
    print(colorama.Fore.GREEN + 'Done\nspend time {:.2f}s'.format(time.time() - starttime))
