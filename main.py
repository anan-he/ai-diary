"""
AI 智能日记 — Python 后端（带用户系统）
========================================
技术栈：FastAPI + SQLite + DeepSeek AI + JWT 认证

运行：cd ai-diary && python -m uvicorn main:app --port 9000
"""

from fastapi import FastAPI, Header, Depends  # Depends 是 FastAPI 的依赖注入，用于"需要登录才能访问"
from fastapi.middleware.cors import CORSMiddleware  # 解决前端跨域问题
from fastapi.responses import HTMLResponse  # 让 FastAPI 可以返回 HTML 页面
from pydantic import BaseModel  # 定义请求体数据格式（前端传什么字段、什么类型）
from datetime import datetime, timedelta  # 处理日期时间，timedelta 用于设置 token 过期时间
from openai import OpenAI  # 用 OpenAI 的接口格式调用 DeepSeek（DeepSeek 兼容 OpenAI SDK）
from dotenv import load_dotenv  # 加载 .env 文件里的环境变量
import sqlite3, hashlib, secrets, jwt, os  # os: 读取环境变量
load_dotenv()  # 启动时自动加载 .env 文件

# ==================== 初始化 ====================

app = FastAPI(title="AI 智能日记", description="全栈 AI 应用")

# CORS 中间件：允许前端页面（不同端口或不同域名）调用后端 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # * 表示允许任何来源访问
    allow_methods=["*"],      # 允许所有 HTTP 方法（GET/POST/PUT/DELETE）
    allow_headers=["*"],      # 允许所有请求头
)

# 优先读 .env 里的 JWT_SECRET，没有就用随机值（兼容没有 .env 的部署环境）
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_EXPIRE_HOURS = 72               # token 有效期 72 小时（3 天），过期需要重新登录

# ==================== DeepSeek AI ====================

# 创建 AI 客户端对象（用 OpenAI SDK 的格式，指向 DeepSeek 的服务器）
ai = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),  # 从 .env 文件读取 API Key，不写在代码里
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),  # 也支持环境变量配置
)

def ai_analyze_mood(content: str) -> str:
    """
    调用 DeepSeek AI 分析日记内容，返回情绪分析和鼓励。
    参数 content：用户写的日记内容（字符串）
    返回：AI 生成的回复文字
    """
    try:
        # 调用 AI 聊天接口
        response = ai.chat.completions.create(
            model="deepseek-chat",  # 使用的模型名称
            messages=[
                # system：设定 AI 的角色和行为（学妹口吻，友好鼓励）
                {"role": "system", "content": "你是一位古灵精怪的学妹。收到日记后，用 2-3 句话判断情绪状态并给一句鼓励。中文回答，像朋友聊天。格式：'情绪：xxx。鼓励：xxx'"},
                # user：把用户的日记内容传进去
                {"role": "user", "content": f"我想写的日记内容：{content}"}
            ],
            temperature=0.8,   # 温度 0~1，越高回答越随机/有创意，越低越保守
            max_tokens=200,    # 最多返回 200 个 token（约 150 个中文字）
        )
        # 从响应里取出 AI 回复的文字，strip() 去掉首尾空白
        return response.choices[0].message.content.strip()
    except Exception as e:
        # 网络出错或 API Key 无效时，返回错误提示而不是崩溃
        return f"AI 分析暂时不可用：{e}"

# ==================== 密码工具 ====================

def hash_password(password: str):  
    """
    把明文密码加密成不可逆的乱码（SHA256 + 随机盐）。
    数据库中永远不存明文密码，只存加密后的结果。
    格式：salt:hash值
    """
    salt = secrets.token_hex(8)  # 生成 8 字节的随机"盐"，让相同密码产生不同哈希值
    h = hashlib.sha256((password + salt).encode()).hexdigest()  # 密码+盐 拼接后做 SHA256 哈希
    return salt + ":" + h  # 把盐和哈希值用冒号拼起来存进数据库

def verify_password(password: str, stored: str) -> bool:
    """
    验证密码：把用户登录时输入的密码，用数据库里存的 salt 重新算一遍哈希，
    比对是否和数据库里存的一致。一致就说明密码正确。
    参数 stored：数据库里存的 "salt:hash" 字符串
    """
    salt, h = stored.split(":")  # 从数据库存储的值里拆出 salt 和原始哈希
    # 用同样的 salt 对输入的密码做哈希，看结果是否一样
    return hashlib.sha256((password + salt).encode()).hexdigest() == h

# ==================== JWT Token ====================

def create_token(user_id: int, username: str) -> str:
    """
    登录成功后生成一个 JWT token（相当于临时通行证）。
    token 里包含了用户信息，有效期 72 小时。
    前端拿到 token 后存起来，后续请求都带着它。
    """
    payload = {
        "user_id": user_id,           # 用户编号
        "username": username,         # 用户名
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)  # 过期时间（UTC 时间 + 72 小时）
    }
    # 用 HS256 算法 + 密钥签名，生成最终的 token 字符串
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> dict:
    """
    验证 token 是否有效：检查签名是否正确、是否过期。
    有效就返回 token 里存的信息（user_id, username）。
    无效（过期或伪造）就抛出异常。
    """
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

def get_current_user(authorization: str = Header(None)):
    """
    从 HTTP 请求头里取出 token，验证后返回用户信息。
    这是 FastAPI 的"依赖注入"函数，每个需要登录的接口都会自动调用它。

    前端请求头格式：Authorization: Bearer <token字符串>

    参数 authorization：FastAPI 自动从请求头 Authorization 字段提取
    返回：{"user_id": 1, "username": "xxx"} 或 None（未登录/token 无效）
    """
    # 没有 Authorization 头，或者格式不对（不以 "Bearer " 开头）
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        # 切掉前面的 "Bearer "，拿到纯 token 字符串
        token = authorization.split(" ")[1]
        return decode_token(token)
    except:
        # token 无效（过期、被篡改、密钥不对）都返回 None
        return None

# ==================== 数据库 ====================

DB_PATH = "diary.db"  # SQLite 数据库文件路径（和 main.py 同一个文件夹）

def get_db():
    """获取数据库连接。每次函数调用都创建新连接（用完记得 close）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 让查询结果可以用 row["字段名"] 的方式取值（类似字典）
    return conn

def init_db():
    """初始化数据库：创建表（如果不存在）、兼容旧数据加列"""
    conn = get_db()

    # 用户表：存储注册用户的信息
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 用户编号，自动递增
            username TEXT NOT NULL UNIQUE,          -- 用户名，不能重复
            password_hash TEXT NOT NULL,            -- 加密后的密码（不是明文！）
            created_at TEXT NOT NULL                -- 注册时间
        )
    """)

    # 日记表：存储每篇日记，通过 user_id 关联到哪个用户写的
    conn.execute("""
        CREATE TABLE IF NOT EXISTS diaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 日记编号，自动递增
            user_id INTEGER NOT NULL DEFAULT 0,    -- 所属用户编号（关联 users 表）
            title TEXT NOT NULL,                    -- 日记标题
            content TEXT NOT NULL,                  -- 日记正文内容
            mood TEXT DEFAULT '😊',                 -- 心情 emoji，默认 😊
            ai_feedback TEXT DEFAULT '',            -- AI 分析后的回复，默认空
            created_at TEXT NOT NULL                -- 创建时间
        )
    """)

    # 兼容旧数据库：如果表是之前创建的、没有 user_id 列，尝试加上
    # ALTER TABLE 如果列已存在会报错，所以用 try/except 忽略
    try:
        conn.execute("ALTER TABLE diaries ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")
    except:
        pass
    try:
        conn.execute("ALTER TABLE diaries ADD COLUMN ai_feedback TEXT DEFAULT ''")
    except:
        pass

    conn.commit()  # 保存所有建表/加列的更改
    conn.close()   # 关闭连接

init_db()  # 启动时就初始化数据库

# ==================== 数据模型（Pydantic 请求体格式） ====================

class RegisterRequest(BaseModel):
    """注册请求体格式"""
    username: str  # 用户名，必传
    password: str  # 密码，必传

class LoginRequest(BaseModel):
    """登录请求体格式"""
    username: str  # 用户名，必传
    password: str  # 密码，必传

class DiaryCreate(BaseModel):
    """新建日记请求体格式"""
    title: str            # 标题，必传
    content: str          # 正文，必传
    mood: str = "😊"       # 心情，选传，默认 😊

# ==================== 首页 ====================

@app.get("/")
def home():
    """返回前端 HTML 页面"""
    with open("frontend.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# ==================== 用户注册 ====================

@app.post("/api/register")
def register(data: RegisterRequest):
    """
    注册新用户。
    前端发送 JSON：{"username": "你的名字", "password": "你的密码"}
    """
    # 校验输入长度
    if len(data.username) < 2 or len(data.password) < 3:
        return {"error": "用户名至少 2 位，密码至少 3 位"}

    conn = get_db()
    # 检查用户名是否已被注册（UNIQUE 约束也会拦，但这里先查一次给友好提示）
    exists = conn.execute("SELECT id FROM users WHERE username = ?", (data.username,)).fetchone()
    if exists:
        conn.close()
        return {"error": "用户名已被注册"}

    # 密码加密后存入数据库（不存明文）
    hashed = hash_password(data.password)
    conn.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
        (data.username, hashed, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()
    return {"message": f"注册成功！欢迎 {data.username}"}


# ==================== 用户登录 ====================

@app.post("/api/login")
def login(data: LoginRequest):
    """
    登录，成功返回 JWT token。
    前端发送 JSON：{"username": "你的名字", "password": "你的密码"}
    前端拿到 token 后存到 localStorage，后续请求都带在 Authorization 头里。
    """
    conn = get_db()
    # 查这个用户名是否存在
    row = conn.execute("SELECT * FROM users WHERE username = ?", (data.username,)).fetchone()
    conn.close()

    if not row:
        return {"error": "用户不存在"}
    # 验证密码是否匹配
    if not verify_password(data.password, row["password_hash"]):
        return {"error": "密码错误"}

    # 生成 token
    token = create_token(row["id"], row["username"])
    return {
        "message": "登录成功",
        "token": token,           # JWT token，前端保存到 localStorage
        "user_id": row["id"],     # 用户编号
        "username": row["username"]  # 用户名（前端用来显示"你好，xxx"）
    }


# ==================== 获取当前用户信息 ====================

@app.get("/api/me")
def get_me(user: dict = Depends(get_current_user)):
    """
    获取当前登录用户的信息。
    Depends(get_current_user) 表示这个接口需要登录，FastAPI 自动调用 get_current_user 验证 token。
    前端刷新页面时用这个接口验证 token 是否还有效。
    """
    if not user:
        return {"error": "未登录"}
    return {"user_id": user["user_id"], "username": user["username"]}

# ==================== 日记接口（全部需要登录）========================

@app.post("/api/diaries")
def create_diary(diary: DiaryCreate, user: dict = Depends(get_current_user)):
    """
    写一篇新日记。
    保存后会调用 AI 分析情绪，把 AI 回复一起存进数据库。
    需要登录（user 参数由 get_current_user 依赖注入提供）。
    """
    if not user:
        return {"error": "请先登录"}

    # 调用 AI 分析日记内容（这是耗时的操作，AI 接口可能要几秒钟）
    feedback = ai_analyze_mood(diary.content)

    conn = get_db()
    # 插入日记到数据库（包括 AI 反馈）
    cursor = conn.execute(
        "INSERT INTO diaries (user_id, title, content, mood, ai_feedback, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user["user_id"], diary.title, diary.content, diary.mood, feedback, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    # 用 lastrowid 查回刚插入的完整记录（通过 row_factory 可以直接转 dict）
    row = conn.execute("SELECT * FROM diaries WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return dict(row)  # 把 Row 对象转成普通字典返回


@app.get("/api/diaries")
def list_diaries(limit: int = 20, user: dict = Depends(get_current_user)):
    """
    获取当前用户的所有日记列表。
    参数 limit：最多返回多少条，默认 20。
    需要登录。
    """
    if not user:
        return {"error": "请先登录"}

    conn = get_db()
    # 只查当前用户的日记，按 id 升序排列（最早的在前）
    rows = conn.execute(
        "SELECT * FROM diaries WHERE user_id = ? ORDER BY id ASC LIMIT ?",
        (user["user_id"], limit)
    ).fetchall()
    conn.close()
    # Row 对象转字典列表（因为 row_factory = sqlite3.Row，所以可以直接 dict(r)）
    return [dict(r) for r in rows]


@app.get("/api/diaries/{diary_id}")
def get_diary(diary_id: int, user: dict = Depends(get_current_user)):
    """
    查看某一篇日记的详情。
    只能看自己的日记（WHERE user_id 限制）。
    需要登录。
    """
    if not user:
        return {"error": "请先登录"}

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM diaries WHERE id = ? AND user_id = ?",  # 同时校验 id 和所属用户
        (diary_id, user["user_id"])
    ).fetchone()
    conn.close()
    if not row:
        return {"error": "日记不存在或无权访问"}
    return dict(row)


@app.delete("/api/diaries/{diary_id}")
def delete_diary(diary_id: int, user: dict = Depends(get_current_user)):
    """
    删除一篇日记。
    只能删自己的日记。
    需要登录。
    """
    if not user:
        return {"error": "请先登录"}

    conn = get_db()
    conn.execute(
        "DELETE FROM diaries WHERE id = ? AND user_id = ?",  # 同时校验，防止删别人的日记
        (diary_id, user["user_id"])
    )
    conn.commit()
    conn.close()
    return {"message": "已删除"}


# ==================== AI 接口（不需登录也能用）========================

@app.post("/api/ai/analyze")
def analyze_text(data: dict):
    """
    独立的 AI 心情分析接口。
    不校验登录，任何用户都可以使用（仅做心情分析，不与日记关联）。
    前端发送 JSON：{"content": "今天心情不太好……"}
    """
    content = data.get("content", "")  # 从 dict 里取 content 字段，没有就默认空字符串
    if not content:
        return {"error": "请输入要分析的内容"}
    return {"analysis": ai_analyze_mood(content)}


# ==================== 统计 ====================

@app.get("/api/stats")
def get_stats(user: dict = Depends(get_current_user)):
    """
    获取当前用户的日记统计（总篇数）。
    需要登录。
    """
    if not user:
        return {"error": "请先登录"}

    conn = get_db()
    # COUNT(*) 统计行数
    total = conn.execute(
        "SELECT COUNT(*) as count FROM diaries WHERE user_id = ?",
        (user["user_id"],)
    ).fetchone()["count"]  # 因为 row_factory = Row，可以用 ["字段名"] 取值
    conn.close()
    return {"total_diaries": total}

@app.put("/api/diaries/{diary_id}")
def update_diary(diary_id: int, diary: DiaryCreate, user: dict = Depends(get_current_user)):
    if not user:
        return {"error": "请先登录"}

    conn = get_db()
    exists = conn.execute(
        "SELECT id FROM diaries WHERE id = ? AND user_id = ?",
        (diary_id, user["user_id"])
    ).fetchone()  # 只查一条，用 fetchone 不是 fetchall

    if not exists:  # exists 是变量，不要加 ()
        conn.close()
        return {"error": "日记不存在或无权修改"}

    # 执行更新：四个 ? 按顺序填入
    conn.execute(
        "UPDATE diaries SET title = ?, content = ?, mood = ? WHERE id = ?",
        (diary.title, diary.content, diary.mood, diary_id)
    )
    conn.commit()
    conn.close()
    return {"message": "修改成功"}