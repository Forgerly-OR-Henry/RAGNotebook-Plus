/**
 * 模块职责：Vue composable 模块，负责复用响应式状态和交互流程。
 * 主要协作：通过导出的类型、函数或组件配置供其他前端模块复用。
 */
import { readonly, ref } from 'vue'

/**
 * 类型：`DialogVariant` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
type DialogVariant = 'default' | 'danger'

/**
 * 接口：`BaseDialogOptions` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface BaseDialogOptions {
  title: string
  message?: string
  confirmText?: string
  cancelText?: string
  variant?: DialogVariant
}

/**
 * 接口：`ConfirmDialogRequest` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface ConfirmDialogRequest extends BaseDialogOptions {
  type: 'confirm'
  resolve: (value: boolean) => void
}

/**
 * 接口：`PromptDialogOptions` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface PromptDialogOptions extends BaseDialogOptions {
  initialValue?: string
  placeholder?: string
}

/**
 * 接口：`PromptDialogRequest` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
interface PromptDialogRequest extends PromptDialogOptions {
  type: 'prompt'
  resolve: (value: string | null) => void
}

/**
 * 类型：`AppDialogRequest` 描述当前业务域中的数据结构。
 * 字段含义应与后端接口、组件入参或本地状态保持一致。
 */
export type AppDialogRequest = ConfirmDialogRequest | PromptDialogRequest

const activeDialog = ref<AppDialogRequest | null>(null)
const queue: AppDialogRequest[] = []

/**
 * 用途：执行showNextDialog相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function showNextDialog() {
  if (activeDialog.value || queue.length === 0) return
  activeDialog.value = queue.shift() || null
}

/**
 * 用途：执行enqueueDialog相关业务逻辑。
 * @param request 调用方传入的request参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
function enqueueDialog(request: AppDialogRequest) {
  queue.push(request)
  showNextDialog()
}

/**
 * 用途：执行confirmDialog相关业务逻辑。
 * @param options 调用方传入的options参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
export function confirmDialog(options: BaseDialogOptions) {
  return new Promise<boolean>((resolve) => {
    enqueueDialog({
      type: 'confirm',
      title: options.title,
      message: options.message,
      confirmText: options.confirmText || '确定',
      cancelText: options.cancelText || '取消',
      variant: options.variant || 'default',
      resolve,
    })
  })
}

/**
 * 用途：执行promptDialog相关业务逻辑。
 * @param options 调用方传入的options参数，用于驱动当前前端逻辑。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
export function promptDialog(options: PromptDialogOptions) {
  return new Promise<string | null>((resolve) => {
    enqueueDialog({
      type: 'prompt',
      title: options.title,
      message: options.message,
      confirmText: options.confirmText || '确定',
      cancelText: options.cancelText || '取消',
      variant: options.variant || 'default',
      initialValue: options.initialValue || '',
      placeholder: options.placeholder || '',
      resolve,
    })
  })
}

/**
 * 用途：执行useAppDialogState相关业务逻辑。
 * 参数：无显式业务参数。
 * @returns 返回计算结果、Promise、状态对象或事件处理结果，具体由调用点消费。
 */
export function useAppDialogState() {
  return {
    activeDialog: readonly(activeDialog),
    cancelDialog() {
      const dialog = activeDialog.value
      if (!dialog) return
      if (dialog.type === 'confirm') {
        dialog.resolve(false)
      } else {
        dialog.resolve(null)
      }
      activeDialog.value = null
      showNextDialog()
    },
    confirmActiveDialog(value?: string) {
      const dialog = activeDialog.value
      if (!dialog) return
      if (dialog.type === 'confirm') {
        dialog.resolve(true)
      } else {
        dialog.resolve(value ?? '')
      }
      activeDialog.value = null
      showNextDialog()
    },
  }
}
