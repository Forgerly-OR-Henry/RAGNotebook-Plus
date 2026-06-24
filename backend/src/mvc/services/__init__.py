"""
模块职责：业务服务模块，负责组织领域用例、数据访问和外部能力协作。

主要协作：本文件只声明当前模块的职责边界，运行时行为由下方函数、类和依赖对象共同完成。
"""

from mvc.services.database_session_manager import DatabaseSessionManager, database_session_manager


class SessionManagerProxy:
    """代理对象，确保访问时 database_session_manager 已被初始化"""

    @property
    def session_manager(self) -> DatabaseSessionManager:
        """
        用途：执行session manager相关业务逻辑。

        参数：无显式业务参数。

        返回：DatabaseSessionManager；返回值供调用方继续编排业务流程或生成接口响应。
        """
        global database_session_manager
        if database_session_manager is None:
            database_session_manager = DatabaseSessionManager()
        return database_session_manager


session_manager = SessionManagerProxy()

__all__ = ["session_manager", "DatabaseSessionManager"]
