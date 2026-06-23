import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

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
  const fileEnv = loadEnv(mode, process.cwd(), '')
  const injected = process.env.RAGNOTEBOOK_ENV_INJECTED?.toLowerCase()
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
  }
})
