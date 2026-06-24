/**
 * 模块职责：前端构建配置模块，负责声明 Vite、ESLint、Tailwind 或 PostCSS 行为。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
