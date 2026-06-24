/**
 * 模块职责：前端构建配置模块，负责声明 Vite、ESLint、Tailwind 或 PostCSS 行为。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import js from '@eslint/js'
import globals from 'globals'
import vue from 'eslint-plugin-vue'
import vueParser from 'vue-eslint-parser'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist', 'src/**/*.tsx']),
  {
    files: ['**/*.ts'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
    ],
    languageOptions: {
      parser: tseslint.parser,
      globals: globals.browser,
    },
  },
  {
    files: ['**/*.vue'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      ...vue.configs['flat/recommended'],
    ],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tseslint.parser,
        ecmaVersion: 'latest',
        sourceType: 'module',
        extraFileExtensions: ['.vue'],
      },
      globals: globals.browser,
    },
    rules: {
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/html-self-closing': 'off',
      'vue/multi-word-component-names': 'off',
    },
  },
])
