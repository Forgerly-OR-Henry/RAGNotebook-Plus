# 流式输出



Listed directory stream_demo
Searched for "level"
Viewed main.py:1-173
Viewed index.html:1-476

在本项目中，**Level 2** 演示了如何使用 **SSE（Server-Sent Events，服务器发送事件）** 协议来模拟 AI 逐字输出的打字机效果。这也是 OpenAI 等主流大模型 API 实现流式输出（Streaming）的标准方案。

下面从 **服务端设计** 和 **客户端接收** 两个方面为你详细讲解 Level 2 的核心逻辑：

---

### 一、 服务端实现 (Python / FastAPI)

服务端代码位于 [main.py](file:///d:/agent_learn/stream_demo/main.py#L56-L102)。

#### 1. SSE 的数据格式规范
SSE 协议有着严格的文本格式要求：
* 每条消息以 `data: ` 开头，后面跟着要传送的数据（通常是 JSON 字符串）。
* 每条消息必须以 **两个换行符 `\n\n`** 结尾，作为一条消息结束的标识。
* 结束时，通常会发送一个约定好的特殊信号（如 `[DONE]`），告知前端流已结束。

格式示例：
```http
data: {"content": "你"}

data: {"content": "好"}

data: {"content": "[DONE]"}
```

#### 2. 服务端关键配置
在 [main.py](file:///d:/agent_learn/stream_demo/main.py#L93-L101) 的 `StreamingResponse` 返回中：
* **`media_type="text/event-stream"`**：这是标准 SSE 要求的媒体类型，浏览器收到后会按流式事件处理。
* **`Cache-Control: no-cache`**：禁用缓存，确保内容能实时推送到客户端。
* **`X-Accel-Buffering: no`**：禁用 Nginx 等反向代理的缓冲区。否则 Nginx 会把数据攒够一定大小再一次性发给前端，导致流式效果失效。

#### 3. 核心异步生成器
```python
async def sse_generator():
    # 逐字发送
    for char in ai_response:
        await asyncio.sleep(0.05)  # 模拟 LLM 生成延迟

        # SSE 格式：data: 内容\n\n
        data = json.dumps({"content": char}, ensure_ascii=False)
        yield f"data: {data}\n\n"

    # 发送结束信号
    yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"
```

---

### 二、 客户端实现 (JavaScript)

前端接收代码位于 [index.html](file:///d:/agent_learn/stream_demo/index.html#L346-L398)。

由于传统的 `fetch` 默认会等待整个 HTTP 响应结束后才返回数据，因此在前端我们需要利用 `Fetch API` 的 `ReadableStream`（可读流）来实时读取服务端推送的字节。

#### 核心解析步骤：
1. **获取流读取器**：
   ```javascript
   const res = await fetch('/stream/sse', { signal: controller2.signal })
   const reader = res.body.getReader() // 拿到流的读取器
   const decoder = new TextDecoder()   // 字节流解码器
   let buffer = ''
   ```
2. **循环读取数据块**：
   通过 `await reader.read()` 每次读取一段缓冲区数据 `value`，直到 `done` 为 `true`。
3. **缓冲区拼接与消息分割**：
   网络传输中，每次接收的数据块（Chunk）可能不完整（例如一条 SSE 消息被截断成了两半）。因此我们需要一个 `buffer` 变量暂存未解析的字符串，并通过 `\n\n` 将其切割：
   ```javascript
   buffer += decoder.decode(value)
   const lines = buffer.split('\n\n')
   buffer = lines.pop() // 最后一个元素可能是不完整的消息，保留到下一次接收时拼接
   ```
4. **解析并渲染**：
   遍历分割出来的完整消息，剔除 `data: ` 前缀并转为 JSON 对象，然后更新到页面上。如果遇到内容是 `[DONE]` 则主动关闭或退出。
   ```javascript
   for (const line of lines) {
     if (!line.startsWith('data: ')) continue
     const jsonStr = line.slice(6) // 移除 "data: "
     const data = JSON.parse(jsonStr)

     if (data.content === '[DONE]') {
       // 结束流处理
       return
     }
     text += data.content // 拼接到页面显示
   }
   ```

---

### 💡 为什么不直接用浏览器的 `EventSource`？
虽然浏览器原生支持 `EventSource` 对象来连接 SSE 接口，但 `EventSource` 默认**只支持 GET 请求**且**无法自定义 Request Header**（例如无法在 Header 里带上 Authorization Token）。
因此，在实际的 AI 聊天应用（如 ChatGPT）中，开发者普遍采用 `fetch` + `ReadableStream` 的方式来自主解析 SSE 流，既支持 POST 请求传递复杂的聊天上下文，也方便设置自定义 Request Headers。

在本项目中，**Level 3** 代表了一个**最接近真实大语言模型（LLM）对话接口**的完整流式实现。

相较于 Level 2，Level 3 引入了 **POST 请求体支持** 和 **结构化的多状态事件流**，更符合生产环境中的真实调用场景（例如调用 OpenAI API 或 LangChain 服务）。

下面为你详细解析 Level 3 的设计要点：

---

### 一、 核心升级点：为什么需要 Level 3？

1. **支持 POST 请求传递复杂参数**
   真实的 LLM 接口不仅需要接收用户的单条消息，往往还需要接收：
   * 完整的历史对话上下文（Chat History）
   * 系统提示词（System Prompt）
   * 采样参数（如 `temperature`, `top_p`, `max_tokens` 等）
   由于这些数据体量大且结构复杂，GET 请求的 URL 传参（Query Parameters）无法满足要求，**必须使用 POST 请求传递 JSON 请求体**。

2. **区分生命周期事件（Event Types）**
   在流式响应中，不仅仅只有“内容文本”，还需要让前端知道流式传输的生命周期。Level 3 通过在 JSON 中定义 `type` 字段，划分了三种状态：
   * **`start`**：连接建立，AI 开始准备输出（可以用来展示“AI 正在思考...”的加载动画）。
   * **`chunk`**：实际的文本数据片段（用于渲染打字效果）。
   * **`done`**：流式结束，并带上**完整的回复内容**（方便前端在对话结束后一次性把完整文本保存到本地或数据库，无需前端自己做字符串拼接）。

---

### 二、 服务端实现 (Python / FastAPI)

代码位于 [main.py](file:///d:/agent_learn/stream_demo/main.py#L104-L157)。

1. **定义请求体 Pydantic 模型**：
   ```python
   class ChatRequest(BaseModel):
       message: str          # 用户输入
       speed: float = 0.05   # 打字速度（秒/字，供演示调节）
   ```

2. **多状态生成器设计**：
   ```python
   async def chat_generator():
       # 1. 发送开始信号
       yield f"data: {json.dumps({'type': 'start'}, ensure_ascii=False)}\n\n"

       # 2. 逐字流式输出
       for char in response_text:
           await asyncio.sleep(request.speed)
           payload = json.dumps({"type": "chunk", "content": char}, ensure_ascii=False)
           yield f"data: {payload}\n\n"

       # 3. 发送结束信号（包含完整回复）
       end_payload = json.dumps({
           "type": "done",
           "full_content": response_text
       }, ensure_ascii=False)
       yield f"data: {end_payload}\n\n"
   ```

---

### 三、 客户端实现 (JavaScript)

代码位于 [index.html](file:///d:/agent_learn/stream_demo/index.html#L400-L467)。

前端通过向 `/stream/chat` 发送 `POST` 请求，并使用自定义逻辑来逐块（Chunk）读取和解析不同类型的事件。

1. **发送 POST 请求并启动流读取**：
   ```javascript
   const res = await fetch('/stream/chat', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ message, speed: 0.04 }),
     signal: controller3.signal
   })
   const reader = res.body.getReader()
   ```

2. **根据 `type` 执行不同分支的渲染**：
   在解析每一行 `data: ` 时，将其 JSON 反序列化后，判断其 `type` 做出不同响应：
   ```javascript
   const data = JSON.parse(line.slice(6))

   if (data.type === 'start') {
     // 1. 改变状态展示，提示用户 AI 正在思考
     setStatus(3, 'streaming', 'AI 正在思考...')
   } else if (data.type === 'chunk') {
     // 2. 收到文字片段，拼接并更新字数和用时
     text += data.content
     charCount++
     setOutput(3, text, true)
   } else if (data.type === 'done') {
     // 3. 接收完毕，移除光标，最终状态归位
     setOutput(3, text)
     setStatus(3, 'done', `完成！${charCount} 个字`)
     return
   }
   ```

---

### 四、 总结与对比

| 阶段        | 传输格式                         | 请求方式 | 适用场景                | 局限性/特点                                             |
| :---------- | :------------------------------- | :------- | :---------------------- | :------------------------------------------------------ |
| **Level 1** | `text/plain` (纯文本)            | GET      | 简单数值流/单向日志输出 | 无法做复杂排版和结构化控制，容易乱码                    |
| **Level 2** | `text/event-stream` (SSE)        | GET      | 简单的打字机效果输出    | 无法携带复杂的请求参数，不便于控制输出属性              |
| **Level 3** | `text/event-stream` (结构化 SSE) | POST     | **生产级 AI 聊天应用**  | 支持复杂请求体 + 细粒度流状态控制（开始、输出中、结束） |
