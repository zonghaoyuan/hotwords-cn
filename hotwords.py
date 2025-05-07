#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import requests
import logging
import os
from typing import Dict, List, Optional, Union, Any
from dotenv import load_dotenv
import google.generativeai as genai

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('hotwords')

# 加载环境变量
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL_NAME = os.getenv("GOOGLE_MODEL_NAME", "gemini-pro")

if not GOOGLE_API_KEY:
    logger.warning("GOOGLE_API_KEY 未在 .env 文件中设置，LLM功能将无法使用")

def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='获取新闻热榜关键词')
    parser.add_argument('-c', '--channel', type=str, help='指定要获取的渠道，如不指定则获取全部渠道')
    parser.add_argument('-l', '--limit', type=int, default=20, help='每个热榜获取前多少条，默认为20')
    parser.add_argument('--cache', action='store_true', default=False, help='是否使用缓存，默认为False（获取最新数据）')
    return parser.parse_args()

def load_prompt(prompt_key: str, default_prompt: str = "") -> str:
    """从prompt.json文件加载指定的提示语"""
    try:
        with open('prompt.json', 'r', encoding='utf-8') as f:
            prompts = json.load(f)
        return prompts.get(prompt_key, default_prompt)
    except FileNotFoundError:
        logger.error("prompt.json 文件未找到")
        return default_prompt
    except json.JSONDecodeError:
        logger.error("prompt.json 文件格式错误")
        return default_prompt

def get_channels(api_base: str) -> List[str]:
    """获取所有可用的渠道列表"""
    url = f"{api_base}/all"
    
    # 设置请求头，模拟浏览器行为
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # 如果状态码不是200，抛出异常
        
        data = response.json()
        if data.get('code') != 200 or 'routes' not in data:
            logger.warning(f"API返回了非预期的数据结构: {data}")
            return []
        
        # 过滤出可用的渠道
        available_channels = []
        for route in data.get('routes', []):
            if route.get('path') is not None and not route.get('message'):
                available_channels.append(route.get('name'))
        
        logger.info(f"成功获取到 {len(available_channels)} 个可用渠道")
        return available_channels
    
    except requests.RequestException as e:
        logger.error(f"获取渠道列表失败: {e}")
        # 这里可以添加回退到预定义列表的逻辑
        logger.warning("使用预定义的渠道列表作为回退")
        # 根据之前的API响应硬编码一个基本的渠道列表作为备选
        fallback_channels = [
            "36kr", "51cto", "acfun", "baidu", "bilibili", "coolapk", "csdn", 
            "douban-group", "douban-movie", "douyin", "earthquake", "genshin", 
            "hellogithub", "history", "honkai", "hupu", "huxiu", "ifanr", 
            "ithome-xijiayi", "ithome", "jianshu", "juejin", "lol", "netease-news", 
            "ngabbs", "nodeseek", "qq-news", "sina-news", "sina", "sspai", 
            "starrail", "thepaper", "tieba", "toutiao", "v2ex", "weatheralarm", 
            "weibo", "weread", "zhihu-daily", "zhihu"
        ]
        return fallback_channels

def get_hotlist_data(api_base: str, channel: str, limit: int, use_cache: bool) -> Dict[str, Any]:
    """获取指定渠道的热榜数据"""
    # 构建请求URL
    cache_param = "true" if use_cache else "false"
    url = f"{api_base}/{channel}?limit={limit}&cache={cache_param}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        return data
    
    except requests.RequestException as e:
        logger.error(f"获取渠道 {channel} 的数据失败: {e}")
        return {}

def extract_keywords_with_google_llm(text: str) -> List[str]:
    """
    使用Google LLM API提取关键词
    
    参数:
        text (str): 要分析的文本，通常是新闻标题和描述的组合
        
    返回:
        List[str]: 从文本中提取的关键词列表
    """
    # 检查API密钥是否已配置
    if not GOOGLE_API_KEY:
        logger.error("GOOGLE_API_KEY未设置，无法使用LLM功能")
        return []
    
    try:
        # 配置Google Generative AI SDK
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # 创建生成式模型实例
        model = genai.GenerativeModel(GOOGLE_MODEL_NAME)
        
        # 加载关键词提取的提示语
        default_prompt = "从以下文本中提取5到10个核心关键词。请确保关键词简洁明了，能准确概括文本主旨。只返回关键词列表，用逗号分隔：\n\n---\n文本开始：\n{text_input}\n文本结束\n---"
        base_prompt = load_prompt("keyword_extraction", default_prompt)
        
        # 替换提示语中的占位符
        formatted_prompt = base_prompt.replace("{text_input}", text)
        
        # 调用模型生成内容
        response = model.generate_content(formatted_prompt)
        
        # 处理响应
        if not response or not hasattr(response, 'text'):
            logger.error("LLM响应格式异常")
            return []
        
        # 解析关键词（假设模型返回的是逗号分隔的关键词列表）
        keywords = [k.strip() for k in response.text.strip().split(',') if k.strip()]
        
        logger.info(f"成功从文本中提取了 {len(keywords)} 个关键词")
        return keywords
    
    except Exception as e:
        logger.error(f"调用LLM提取关键词时发生错误: {e}")
        return []

def main():
    # 解析命令行参数
    args = parse_arguments()
    
    # API基础URL
    api_base = "https://dailyhotapi-gamma.vercel.app"
    
    # 确定要处理的渠道列表
    channels_to_process = []
    if args.channel:
        # 如果指定了特定渠道，只处理该渠道
        channels_to_process = [args.channel]
        logger.info(f"仅处理指定渠道: {args.channel}")
    else:
        # 否则获取所有可用渠道
        channels_to_process = get_channels(api_base)
        logger.info(f"将处理以下渠道: {', '.join(channels_to_process)}")
    
    # 检查是否有渠道可以处理
    if not channels_to_process:
        logger.error("没有找到可处理的渠道，退出程序")
        return
    
    # 存储所有渠道的关键词
    all_channel_keywords = {}
    
    # 遍历处理每个渠道
    for channel in channels_to_process:
        logger.info(f"正在处理渠道: {channel}")
        
        # 获取热榜数据
        hotlist_data = get_hotlist_data(api_base, channel, args.limit, args.cache)
        
        # 检查是否成功获取数据
        if not hotlist_data or 'data' not in hotlist_data or not hotlist_data['data']:
            logger.warning(f"未能获取到渠道 {channel} 的有效数据，跳过")
            continue
        
        # 使用title作为键（如果存在），否则使用name
        channel_display_name = hotlist_data.get('title', hotlist_data.get('name', channel))
        
        # 提取热榜条目文本
        channel_texts = []
        for item in hotlist_data['data']:
            item_text = item.get('title', '')
            if item.get('desc'):
                item_text += ' ' + item.get('desc')
            channel_texts.append(item_text)
        
        # 组合所有文本，用于一次性提取关键词
        combined_text = '\n'.join(channel_texts)
        
        # 使用LLM提取关键词
        keywords = extract_keywords_with_google_llm(combined_text)
        
        # 存储关键词
        if keywords:
            all_channel_keywords[channel_display_name] = keywords
            logger.info(f"从渠道 {channel_display_name} 提取了 {len(keywords)} 个关键词")
        else:
            logger.warning(f"未能从渠道 {channel_display_name} 提取到关键词")
    
    # 输出结果
    if all_channel_keywords:
        print(json.dumps(all_channel_keywords, ensure_ascii=False, indent=2))
        logger.info(f"成功处理了 {len(all_channel_keywords)} 个渠道的关键词")
    else:
        logger.error("未能从任何渠道提取关键词")

if __name__ == "__main__":
    main()