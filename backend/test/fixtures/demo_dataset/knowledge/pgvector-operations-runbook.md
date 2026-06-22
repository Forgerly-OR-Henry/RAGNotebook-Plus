# pgvector 运维排查手册

本手册用于本地开发和冒烟测试。目标是让开发者快速定位 PostgreSQL、Alembic 和 pgvector 相关问题。

## 初始化检查

1. 确认 PostgreSQL 服务已启动，并且 DATABASE_URL 指向同一个库。
2. 确认数据库用户有权限执行 `CREATE EXTENSION vector`。
3. 查询 `pg_extension`，确认 vector 扩展已经安装。
4. 查询 `knowledge_documents` 和 `index_chunks`，确认迁移已经完成。

## 维度检查

`EMBEDDING_DIM` 必须与当前嵌入模型输出维度一致。表一旦创建，`index_chunks.embedding` 的维度不会自动跟随模型变化。如果从 1024 维模型切换到其他维度模型，应重建本地测试库或新增迁移。

## 数据清理

演示数据只允许清理固定 demo_user 下的记录。知识库清理应按 user_id 和 original_filename 定位，避免误删其他用户上传的文档。
