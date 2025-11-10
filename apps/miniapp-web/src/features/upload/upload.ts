import { apiUrl } from '../../lib/api'

export type UploadResponse = {
  ok: boolean
  saved: boolean
  filename: string
  bytes: number
  telegram_sent?: boolean
  error?: string
}

const DEFAULT_ERROR = 'Upload failed. Please try again.'

function buildEndpoints(): string[] {
  const candidates = [
    apiUrl('/briefs/upload'),
    apiUrl('/api/briefs/upload'),
    '/briefs/upload',
    '/api/briefs/upload',
  ]
  const unique = new Set<string>()
  const result: string[] = []
  for (const candidate of candidates) {
    if (!candidate || unique.has(candidate)) continue
    unique.add(candidate)
    result.push(candidate)
  }
  return result
}

async function parseJsonSafe(response: Response): Promise<any | undefined> {
  try {
    return await response.clone().json()
  } catch {
    return undefined
  }
}

export async function submitBriefUpload(form: FormData): Promise<UploadResponse> {
  const endpoints = buildEndpoints()
  let lastError: Error | null = null

  for (const endpoint of endpoints) {
    try {
      const res = await fetch(endpoint, { method: 'POST', body: form })
      const payload = await parseJsonSafe(res)

      if (!res.ok || !payload?.ok || !payload?.saved) {
        const message =
          payload?.error || payload?.detail || (!res.ok ? `${res.status} ${res.statusText}` : '') || DEFAULT_ERROR
        lastError = new Error(message)
        continue
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
      lastError = error instanceof Error ? error : new Error(DEFAULT_ERROR)
    }
  }

  throw lastError ?? new Error(DEFAULT_ERROR)
}


