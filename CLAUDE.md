# AI 智能日记

FastAPI + SQLite + DeepSeek AI + JWT 全栈日记应用。

## 运行

```bash
cd C:\Users\陈boyuan\Desktop\ai-diary
python -m uvicorn main:app --port 9000
```

然后浏览器打开 `frontend.html` 即可使用。

## 技术栈

- 后端：Python FastAPI (`main.py`)，端口 9000
- 前端：单页 HTML (`frontend.html`)，原生 JS，无框架
- 数据库：SQLite (`diary.db`)，两个表：`users` 和 `diaries`
- AI：DeepSeek API（`deepseek-chat` 模型），用于情绪分析
- 认证：JWT Token（Bearer 方式）

## 项目结构

```
ai-diary/
├── main.py          # 后端全部代码（API + AI + 数据库 + JWT）
├── frontend.html    # 前端全部代码（登录/注册/写日记/AI分析）
├── diary.db         # SQLite 数据库文件
└── CLAUDE.md        # 本文件
```

## 功能列表

- 用户注册 / 登录（JWT Token 认证，有效期 72 小时）
- 写日记 + 选择心情 emoji
- 保存日记后 AI 自动分析情绪并生成鼓励回复
- 日记列表查看、删除
- 日记统计（总数）
- 独立的 AI 心情分析入口（不需登录）

## 已知问题 / 待改进

1. **API Key 硬编码**：DeepSeek API Key 直接写在 `main.py` 第 31 行，应改为环境变量 `DEEPSEEK_API_KEY`
2. **JWT Secret 每次重启随机生成**：`main.py` 第 25 行用 `secrets.token_hex(32)`，服务重启后所有旧 token 失效，应改为固定值或从环境变量读取
3. **无前端构建步骤**：只有一个 `frontend.html`，需手动在浏览器打开
4. 缺少 README.md
5. 代码未推送到 GitHub

## 注意事项

- 这是学习项目，用户是云南财经大学大三信管专业学生，代码基础较弱
- 用户的目标是把项目写进简历
- 修改代码时多加中文注释解释原理
