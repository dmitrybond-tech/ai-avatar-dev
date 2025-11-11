import { apiFetch } from '../../lib/api'

export type UploadResponse = {
  ok: boolean
  saved: boolean
  filename: string
  bytes: number
  telegram_sent?: boolean
  error?: string
}

const DEFAULT_ERROR = 'Upload failed. Please try again.'

async function parseJsonSafe(response: Response): Promise<any | undefined> {
  try {
    return await response.clone().json()
  } catch {
    return undefined
  }
}

export async function submitBriefUpload(form: FormData): Promise<UploadResponse> {
  try {
    const res = await apiFetch('/briefs/upload', { method: 'POST', body: form })
    const payload = await parseJsonSafe(res)

    if (!res.ok || !payload?.ok || !payload?.saved) {
      const message =
        payload?.error || payload?.detail || (!res.ok ? `${res.status} ${res.statusText}` : '') || DEFAULT_ERROR
      throw new Error(message)
    }

    return {
      ok: Boolean(payload.ok),
      saved: Boolean(payload.saved),
      filename: String(payload.filename ?? ''),
      bytes: Number(payload.bytes ?? 0),
      telegram_sent: payload.telegram_sent === undefined ? undefined : Boolean(payload.telegram_sent),
      error: payload.error,
    }
  } catch (error) {
    throw error instanceof Error ? error : new Error(DEFAULT_ERROR)
  }
}


