/**
 * Copy text to clipboard. Uses Clipboard API when available,
 * otherwise falls back to a temporary textarea (needed on non-HTTPS).
 */
export async function copyTextToClipboard(text: string): Promise<void> {
  const value = text ?? ''

  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value)
    return
  }

  const textarea = document.createElement('textarea')
  textarea.value = value
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.style.top = '0'
  document.body.appendChild(textarea)
  textarea.focus()
  textarea.select()

  try {
    const ok = document.execCommand('copy')
    if (!ok) {
      throw new Error('Copy command was rejected')
    }
  } finally {
    document.body.removeChild(textarea)
  }
}
