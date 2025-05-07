# 热搜关键词提取工具

一个基于Python的工具，用于从各大热榜网站获取热搜信息，并使用Google LLM API提取关键词用于SEO优化。

## 功能特点

- 支持多个热榜源（微博、知乎、百度等40+个渠道）
- 可选参数控制获取数量和是否使用缓存
- 使用Google Gemini模型提取SEO友好的关键词
- 自定义关键词提取的提示语模板

## 安装

1. 克隆仓库
```bash
git clone https://github.com/zonghao-mars/hotwords-cn.git
cd hotwords-cn
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境
- 复制`.env.example`为`.env`并填入自己的Google API密钥

## 使用方法

```bash
# 获取所有渠道的热榜关键词
python hotwords.py

# 指定特定渠道
python hotwords.py -c weibo

# 指定多个渠道
python hotwords.py -c weibo zhihu bilibili

# 自定义获取数量（默认为20）
python hotwords.py -l 10

# 使用缓存数据
python hotwords.py --cache
```

## 输出

脚本将以JSON格式输出各个渠道的关键词列表：

```json
{
  "微博": ["关键词1", "关键词2", "关键词3"],
  "知乎": ["关键词1", "关键词2", "关键词3"]
}
```

## 自定义提示语

可以修改`prompt.json`文件中的提示语模板，以调整关键词提取的策略。

## 数据来源

本工具使用的热榜API基于[DailyHotApi](https://github.com/imsyy/DailyHotApi)项目。