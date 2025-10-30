import { useState } from "react";
import { postChat } from "../api/client";

type Msg = { id: string; role: 'user' | 'assistant'; text: string };

export function ChatBox() {
  const [msgs, setMsgs] = useState<Msg[]>([
    { id: 'm1', role: 'assistant', text: 'Привет! Я ассистент. Чем помочь?' }
  ]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);

  const send = async () => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    const userMsg: Msg = { id: String(Date.now()), role: 'user', text: trimmed };
    setMsgs((m) => [...m, userMsg]);
    setText("");
    setSending(true);
    try {
      const r = await postChat(trimmed);
      setMsgs((m) => [...m, { id: userMsg.id + '-r', role: 'assistant', text: r.reply }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="grid gap-2">
      <div className="grid gap-2 max-h-64 overflow-auto">
        {msgs.map((m) => (
          <div key={m.id} className={m.role === 'user' ? 'text-right' : 'text-left'}>
            <span className={`inline-block px-3 py-2 rounded ${m.role==='user'?'bg-black text-white':'bg-gray-100'}`}>{m.text}</span>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input className="flex-1 border border-gray-300 rounded px-3 h-10" value={text} onChange={(e)=>setText(e.target.value)} placeholder="Type a message" />
        <button className="h-10 px-4 rounded bg-black text-white" onClick={send} disabled={sending}>Send</button>
      </div>
    </div>
  );
}


