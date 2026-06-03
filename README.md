# AI智能日记

FastAPI + SQLite + DeepSeek AI + JWT 全栈日记应用，已部署上线。

## 在线访问

[http://121.40.89.252:9000/](http://121.40.89.252:9000/)

## 功能

- 用户注册 / 登录（JWT Token 认证）
- 写日记 + 选择心情 emoji
- AI 自动分析情绪并生成鼓励回复（DeepSeek）
- 日记列表查看、编辑、删除
- 独立的 AI 心情分析入口
- 多用户数据隔离

## 技术栈

| 分类 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| 数据库 | SQLite |
| AI 模型 | DeepSeek Chat |
| 认证 | JWT (HS256) |
| 密码加密 | SHA256 + 随机盐 |
| 前端 | 原生 HTML + CSS + JavaScript |
| 部署 | 阿里云 ECS + Ubuntu + Nginx（待加） |

## 本地运行

```bash
# 1. 安装依赖
pip install fastapi uvicorn pydantic openai python-dotenv PyJWT

# 2. 配置环境变量（复制 .env.example 为 .env，填入密钥）
cp .env.example .env

# 3. 启动服务
python -m uvicorn main:app --port 9000

# 4. 浏览器打开
http://127.0.0.1:9000/
```
