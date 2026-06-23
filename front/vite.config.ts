import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import fs from 'fs'

function envFileKeys(filePath: string): Set<string> {
  if (!fs.existsSync(filePath)) {
    return new Set()
  }

  return new Set(
    fs
      .readFileSync(filePath, 'utf-8')
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith('#') && line.includes('='))
      .map((line) => line.split('=', 1)[0].trim().replace(/^\uFEFF/, '')),
  )
}

function validateEnvDeclaresTemplateKeys(envPath: string, examplePath: string): void {
  if (!fs.existsSync(envPath) || !fs.existsSync(examplePath)) {
    return
  }

  const envKeys = envFileKeys(envPath)
  const missing = Array.from(envFileKeys(examplePath)).filter((key) => !envKeys.has(key))
  if (missing.length > 0) {
    throw new Error(
      `${envPath} is missing config fields: ${missing.join(', ')}. ` +
        `Copy the missing keys from ${examplePath}; values may be empty or use template defaults, but fields must be explicit.`,
    )
  }
}

function requiredEnv(env: Record<string, string>, key: string): string {
  const value = env[key]?.trim()
  if (!value) {
    throw new Error(`${key} is required in front/.env`)
  }
  return value
}

function envInt(env: Record<string, string>, key: string): number {
  const value = Number(requiredEnv(env, key))
  if (!Number.isInteger(value)) {
    throw new Error(`${key} must be an integer in front/.env`)
  }
  return value
}

function processEnv(): Record<string, string> {
  return Object.fromEntries(
    Object.entries(process.env).filter((entry): entry is [string, string] => entry[1] !== undefined),
  )
}

export default defineConfig(({ mode }) => {
  const injected = process.env.RAGNOTEBOOK_ENV_INJECTED?.toLowerCase()
  if (!['1', 'true', 'yes', 'on'].includes(injected || '')) {
    validateEnvDeclaresTemplateKeys(path.resolve(__dirname, '.env'), path.resolve(__dirname, '.env.example'))
  }

  const fileEnv = loadEnv(mode, process.cwd(), '')
  const env = ['1', 'true', 'yes', 'on'].includes(injected || '') ? { ...fileEnv, ...processEnv() } : fileEnv
  const backendTarget = requiredEnv(env, 'VITE_BACKEND_TARGET')

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: envInt(env, 'FRONTEND_PORT'),
      host: requiredEnv(env, 'FRONTEND_HOST'),
      proxy: {
        '/chat/agent/': { target: backendTarget, changeOrigin: true, ws: true },
        '/chat/rag/': { target: backendTarget, changeOrigin: true },
        '/chat/quiz/': { target: backendTarget, changeOrigin: true },
        '/chat/session/': { target: backendTarget, changeOrigin: true },
        '/chat/sessions': { target: backendTarget, changeOrigin: true },
        '/chat/reorder': { target: backendTarget, changeOrigin: true },
        '/projects': { target: backendTarget, changeOrigin: true, timeout: 0, proxyTimeout: 0 },
        '/knowledge/': { target: backendTarget, changeOrigin: true, timeout: 0, proxyTimeout: 0 },
        '/note/': { target: backendTarget, changeOrigin: true },
        '/note-template/': { target: backendTarget, changeOrigin: true },
        '/quick-test/': { target: backendTarget, changeOrigin: true },
        '/mindmaps/': { target: backendTarget, changeOrigin: true },
        '/health': { target: backendTarget, changeOrigin: true },
        '/user': { target: backendTarget, changeOrigin: true },
        '/file': { target: backendTarget, changeOrigin: true },
        '/media': { target: backendTarget, changeOrigin: true },
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules/@tiptap') || id.includes('node_modules/prosemirror')) {
              return 'editor-prosemirror'
            }
            if (id.includes('node_modules/lowlight') || id.includes('node_modules/turndown')) {
              return 'editor-tools'
            }
            if (id.includes('node_modules/marked') || id.includes('node_modules/dompurify')) {
              return 'markdown-rendering'
            }
          },
        },
      },
    },
  }
})
