# Bili Up Finder

中文 | [English](README_en.md)

## 项目简介

Bili Up Finder 是一个工具，旨在帮助用户搜索和分析 Bilibili 内容创作者（Up主）。它提供了关键词扩展、相关性判断以及使用 AI 助手生成报告等功能。

## 配置说明

1. 确保已安装 Python 3.12 或更高版本。
2. 使用 `pip` 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 在环境变量中配置 OpenAI 的 API 密钥：
   ```bash
   export OPENAI_API_KEY="your_api_key_here"
   ```

## 使用方法

运行主脚本以生成报告：
```bash
python -m bili_up_finder.web_builder
```

## 使用示例

生成搜索查询的报告：
```bash
python -m bili_up_finder.web_builder --query "示例关键词"
```

## 功能特性

- **关键词扩展**：自动扩展搜索查询，生成相关词语。
- **相关性判断**：判断视频或用户空间是否与搜索查询相关。
- **报告生成**：创建 HTML 报告总结搜索结果。

## 许可证

本项目使用 MIT 许可证授权。