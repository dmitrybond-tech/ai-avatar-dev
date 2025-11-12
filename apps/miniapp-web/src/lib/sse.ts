import { apiUrl } from "../shared/api";

export function streamReply(
  text: string,
  onToken: (tok: string) => void,
  onEnd: () => void
) {
  const url = apiUrl("/chat/stream?" + new URLSearchParams({ text, lang: "ru" }));
  const es = new EventSource(url);
  es.addEventListener("token", (ev: MessageEvent) => {
    const data = JSON.parse((ev as any).data || "{}");
    if (data?.t) onToken(data.t);
  });
  es.addEventListener("end", () => { es.close(); onEnd(); });
  es.addEventListener("error", () => es.close());
  return () => es.close();
}

