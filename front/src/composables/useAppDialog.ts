import { readonly, ref } from 'vue'

type DialogVariant = 'default' | 'danger'

interface BaseDialogOptions {
  title: string
  message?: string
  confirmText?: string
  cancelText?: string
  variant?: DialogVariant
}

interface ConfirmDialogRequest extends BaseDialogOptions {
  type: 'confirm'
  resolve: (value: boolean) => void
}

interface PromptDialogOptions extends BaseDialogOptions {
  initialValue?: string
  placeholder?: string
}

interface PromptDialogRequest extends PromptDialogOptions {
  type: 'prompt'
  resolve: (value: string | null) => void
}

export type AppDialogRequest = ConfirmDialogRequest | PromptDialogRequest

const activeDialog = ref<AppDialogRequest | null>(null)
const queue: AppDialogRequest[] = []

function showNextDialog() {
  if (activeDialog.value || queue.length === 0) return
  activeDialog.value = queue.shift() || null
}

function enqueueDialog(request: AppDialogRequest) {
  queue.push(request)
  showNextDialog()
}

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
