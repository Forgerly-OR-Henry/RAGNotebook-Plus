# RAGNotebook 测试知识库发布说明

本 Markdown 文件用于验证 `.md` 上传、Markdown 文本解析、切片以及检索。关键词：向量索引、权限隔离、上传失败处理、知识库文件夹、图片预览。

## 上传主流程

1. 用户在知识库页面选择多个文件。
2. 前端通过 `FormData` 提交文件，并监听 SSE 上传进度。
3. 后端校验文件大小和类型，保存原文件。
4. 解析器提取文本并生成切片。
5. 索引仓库写入向量索引，详情页展示预览和切片。

## 功能覆盖表

| 能力 | 测试点 | 期望结果 |
|---|---|---|
| 向量索引 | 上传后搜索关键词 | 能命中相关片段 |
| 权限隔离 | 不同用户上传同名文件 | 只看到自己的文档 |
| 知识库文件夹 | 上传到当前文件夹 | 文档归属正确 |
| 图片预览 | 打开 DOCX/PPTX/PDF 渲染预览 | 嵌入图片正常显示 |

## 公式渲染样例

行内公式用于验证正文中的数学表达式，例如向量相似度可以写作 $\cos(\theta)=\frac{A\cdot B}{\|A\|\|B\|}$，上传后应在 Markdown 预览中保持在同一行。

块级公式用于验证独立公式排版：

$$
\mathrm{score}(q,d)=\alpha\cdot \mathrm{BM25}(q,d)+(1-\alpha)\cdot \cos(e_q,e_d)
$$

也测试 LaTeX bracket 形式：

\[
P(\text{命中}\mid q)=\frac{\text{相关切片数}}{\text{候选切片总数}}
\]

## 示例配置片段

```yaml
knowledge_upload_test:
  mode: positive
  files: [txt, md, docx, pptx, pdf]
  expected_success_count: 5
  keywords:
    - 向量索引
    - 上传失败处理
    - 图片预览
```

## 验收提示

如果上传完成但检索不到“图片预览”，优先检查切片写入和向量索引状态；如果 PDF、Word 或 PPT 的图片不显示，优先检查详情页原样预览接口和浏览器 iframe 渲染。
